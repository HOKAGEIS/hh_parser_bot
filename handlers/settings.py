# handlers/settings.py (исправленный код)
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

import database as db
import keyboards as kb
from hh_api import hh
from config import Config

router = Router()


class SettingsStates(StatesGroup):
    entering_analytics_query = State()
    adding_exclude_word = State()
    entering_city = State()


# ==================== ВСПОМОГАТЕЛЬНОЕ ====================

def settings_cities_kb() -> InlineKeyboardBuilder:
    """
    Отдельная клавиатура для настроек (НЕ kb.cities_kb),
    чтобы callback_data были settings_set_city_*
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌍 Любой город", callback_data="settings_set_city_any")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="settings_enter_city_manual")
    )

    # популярные города
    for city_id, city_name in list(Config.POPULAR_CITIES.items())[:10]:
        builder.row(
            InlineKeyboardButton(text=f"📍 {city_name}", callback_data=f"settings_set_city_{city_id}")
        )

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_settings"))
    return builder


# ==================== НАСТРОЙКИ (меню) ====================

@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message, state: FSMContext):
    await state.clear()
    await db.ensure_user(message.from_user.id, message.from_user.username)
    user = await db.get_user(message.from_user.id)

    await message.answer(
        "⚙️ <b>Настройки</b>\n\nНастройте параметры поиска:",
        reply_markup=kb.settings_kb(user),
        parse_mode="HTML",
    )


# ==================== МОИ ОТКЛИКИ ====================

@router.message(F.text == "📨 Мои отклики")
async def show_applications(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📨 <b>Мои отклики</b>\n\n"
        "🚧 <i>Функция в разработке</i>\n\n"
        "Для откликов на вакансии требуется интеграция с API HH.ru.\n\n"
        "Следите за обновлениями!",
        reply_markup=kb.main_menu_kb(message.from_user.id),
        parse_mode="HTML",
    )


# ==================== ПИСЬМА ====================

@router.message(F.text == "✉️ Письма")
async def show_letters(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "✉️ <b>Сопроводительные письма</b>\n\n"
        "🚧 <i>Функция в разработке</i>\n\n"
        "Скоро вы сможете:\n"
        "• Создавать шаблоны писем\n"
        "• Редактировать письма\n"
        "• Выбирать письмо при отклике\n\n"
        "Следите за обновлениями!",
        reply_markup=kb.main_menu_kb(message.from_user.id),
        parse_mode="HTML",
    )


# ==================== НАСТРОЙКИ: ГОРОД ====================

@router.callback_query(F.data == "settings_city")
async def settings_city(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)

    try:
        await callback.message.edit_text(
            "📍 <b>Город по умолчанию</b>\n\nВыберите из списка или введите вручную:",
            reply_markup=settings_cities_kb().as_markup(),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "settings_enter_city_manual")
async def settings_enter_city_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsStates.entering_city)
    try:
        await callback.message.edit_text(
            "📍 <b>Введите город по умолчанию:</b>\n\n<i>Например: Казань</i>",
            reply_markup=kb.back_kb("back_to_settings"),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


@router.message(SettingsStates.entering_city, F.text)
async def settings_city_manual_text(message: Message, state: FSMContext):
    city_name = (message.text or "").strip()
    if len(city_name) < 2:
        await message.answer("⚠️ Слишком короткое название. Введите ещё раз.")
        return

    await message.answer("🔍 Ищу город...")

    cities = await hh.search_area(city_name)
    if not cities:
        await message.answer("😔 Город не найден. Попробуйте другое название.")
        return

    if len(cities) == 1:
        c = cities[0]
        cid = str(c.get("id"))
        name = c.get("text") or c.get("name") or city_name
        await db.update_user_settings(message.from_user.id, city_id=cid, city_name=name)
        await state.clear()

        user = await db.get_user(message.from_user.id)
        await message.answer(
            f"✅ Город по умолчанию: <b>{name}</b>",
            reply_markup=kb.settings_kb(user),
            parse_mode="HTML",
        )
        return

    # несколько вариантов — сохраняем mapping в state и показываем кнопки по id
    variants = {str(c.get("id")): (c.get("text") or c.get("name") or "Город") for c in cities}
    await state.update_data(city_variants=variants)
    await state.set_state(None)

    builder = InlineKeyboardBuilder()
    for cid, name in list(variants.items())[:20]:
        builder.row(InlineKeyboardButton(text=f"📍 {name[:60]}", callback_data=f"settings_set_city_{cid}"))
    builder.row(InlineKeyboardButton(text="🌍 Любой город", callback_data="settings_set_city_any"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_settings"))

    await message.answer("Выберите город:", reply_markup=builder.as_markup())


@router.message(SettingsStates.entering_city)
async def settings_city_manual_not_text(message: Message):
    await message.answer("⚠️ Введите город текстом.")


@router.callback_query(F.data == "settings_set_city_any")
async def settings_set_city_any(callback: CallbackQuery, state: FSMContext):
    await db.update_user_settings(callback.from_user.id, city_id=None, city_name=None)
    await state.clear()

    user = await db.get_user(callback.from_user.id)
    try:
        await callback.message.edit_text(
            "✅ Город по умолчанию сброшен.",
            reply_markup=kb.settings_kb(user),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("settings_set_city_"))
async def settings_set_city(callback: CallbackQuery, state: FSMContext):
    city_id = callback.data.replace("settings_set_city_", "", 1)

    data = await state.get_data()
    name = (data.get("city_variants") or {}).get(city_id)  # может быть None

    await db.update_user_settings(callback.from_user.id, city_id=city_id, city_name=name)
    await state.clear()

    user = await db.get_user(callback.from_user.id)
    try:
        await callback.message.edit_text(
            f"✅ Город по умолчанию: <b>{user.get('city_name', 'не выбран') if user else 'не выбран'}</b>",
            reply_markup=kb.settings_kb(user),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer("✅ Сохранено")


# ==================== НАСТРОЙКИ: ТОЛЬКО С ЗАРПЛАТОЙ ====================

@router.callback_query(F.data == "settings_salary_toggle")
async def settings_salary_toggle(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    current_setting = user.get('only_with_salary', False) if user else False
    new_value = not current_setting

    await db.update_user_settings(callback.from_user.id, only_with_salary=new_value)
    user = await db.get_user(callback.from_user.id)

    try:
        await callback.message.edit_text(
            "⚙️ <b>Настройки</b>",
            reply_markup=kb.settings_kb(user),
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer(f"✅ {'Включено' if new_value else 'Выключено'}")


# ==================== НАСТРОЙКИ: СЛОВА-ИСКЛЮЧЕНИЯ ====================

@router.callback_query(F.data == "settings_exclude")
async def settings_exclude(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)

    user = await db.get_user(callback.from_user.id)
    words = user.get('exclude_words', []) if user else []

    text = "🚫 <b>Слова-исключения</b>\n\n"
    text += (", ".join([f"<code>{w}</code>" for w in words]) if words else "Список пуст.")

    try:
        await callback.message.edit_text(
            text,
            reply_markup=kb.settings_exclude_kb(words),  # <-- кнопки settings_remove_exclude_{index}
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "settings_add_exclude")
async def settings_add_exclude(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsStates.adding_exclude_word)

    try:
        await callback.message.edit_text(
            "🚫 <b>Добавить слово-исключение</b>\n\n"
            "Введите слово:\n\n"
            "<i>Примеры: стажёр, junior, без опыта</i>",
            reply_markup=kb.back_kb("back_to_settings"),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


@router.message(SettingsStates.adding_exclude_word, F.text)
async def process_exclude_word(message: Message, state: FSMContext):
    word = (message.text or "").strip().lower()
    if len(word) < 2:
        await message.answer("⚠️ Слишком короткое")
        return
    if len(word) > 50:
        await message.answer("⚠️ Слишком длинное (макс 50)")
        return

    user = await db.get_user(message.from_user.id)
    words = user.get('exclude_words', []) if user else []

    max_words = getattr(Config, "MAX_EXCLUDE_WORDS", 20)
    if len(words) >= max_words:
        await message.answer(f"⚠️ Максимум {max_words} слов")
        return

    if word not in words:
        words.append(word)
        await db.update_user_settings(message.from_user.id, exclude_words=words)

    await state.clear()

    await message.answer(
        f"✅ Добавлено: <b>{word}</b>",
        reply_markup=kb.settings_exclude_kb(words),
        parse_mode="HTML",
    )


@router.message(SettingsStates.adding_exclude_word)
async def process_exclude_word_not_text(message: Message):
    await message.answer("⚠️ Введите слово текстом.")


@router.callback_query(F.data.startswith("settings_remove_exclude_"))
async def settings_remove_exclude(callback: CallbackQuery):
    # ВАЖНО: теперь удаляем по индексу, а не по слову
    idx_str = callback.data.replace("settings_remove_exclude_", "", 1)
    try:
        idx = int(idx_str)
    except ValueError:
        await callback.answer("Ошибка кнопки", show_alert=True)
        return

    user = await db.get_user(callback.from_user.id)
    words = user.get('exclude_words', []) if user else []

    if not (0 <= idx < len(words)):
        await callback.answer("Уже удалено", show_alert=False)
        return

    words.pop(idx)
    await db.update_user_settings(callback.from_user.id, exclude_words=words)

    try:
        await callback.message.edit_text(
            "🚫 <b>Слова-исключения</b>\n\n" +
            (", ".join([f"<code>{w}</code>" for w in words]) if words else "Список пуст."),
            reply_markup=kb.settings_exclude_kb(words),
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer("✅ Удалено")


@router.callback_query(F.data == "settings_clear_exclude")
async def settings_clear_exclude(callback: CallbackQuery):
    await db.update_user_settings(callback.from_user.id, exclude_words=[])

    try:
        await callback.message.edit_text(
            "🚫 <b>Слова-исключения</b>\n\n✅ Очищено",
            reply_markup=kb.settings_exclude_kb([]),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer("🗑 Очищено")


# ==================== НАСТРОЙКИ: УВЕДОМЛЕНИЯ ====================

@router.callback_query(F.data == "settings_notifications")
async def settings_notifications(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    enabled = user.get('notifications_enabled', True) if user else True

    await callback.message.edit_text(
        "🔔 <b>Автоуведомления</b>\n\n"
        "Бот будет присылать новые вакансии по вашим подпискам автоматически.\n\n"
        f"Статус: {'✅ Включены' if enabled else '❌ Выключены'}",
        reply_markup=kb.notifications_kb(enabled),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    current_setting = user.get('notifications_enabled', True) if user else True
    new_value = not current_setting

    await db.update_user_settings(callback.from_user.id, notifications_enabled=new_value)

    await callback.message.edit_text(
        "🔔 <b>Автоуведомления</b>\n\n"
        f"{'✅ Уведомления включены!' if new_value else '❌ Уведомления выключены'}",
        reply_markup=kb.notifications_kb(new_value),
        parse_mode="HTML",
    )
    await callback.answer()


# ==================== НАСТРОЙКИ: СБРОС/НАЗАД ====================

@router.callback_query(F.data == "settings_reset")
async def settings_reset(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await db.update_user_settings(
        callback.from_user.id,
        city_id=None,
        city_name=None,
        experience=None,
        schedule=None,
        salary_from=None,
        only_with_salary=False,
        exclude_words=[],
        notifications_enabled=True,
    )

    user = await db.get_user(callback.from_user.id)

    try:
        await callback.message.edit_text(
            "⚙️ <b>Настройки</b>\n\n✅ Сброшено!",
            reply_markup=kb.settings_kb(user),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer("🔄 Сброшено")


@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await db.get_user(callback.from_user.id)

    try:
        await callback.message.edit_text(
            "⚙️ <b>Настройки</b>",
            reply_markup=kb.settings_kb(user),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


# ==================== АНАЛИТИКА ====================

@router.message(F.text == "📊 Аналитика")
async def show_analytics_prompt(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SettingsStates.entering_analytics_query)
    await message.answer(
        "📊 <b>Аналитика зарплат</b>\n\n"
        "Введите профессию:\n\n"
        "<i>Пример: Python разработчик</i>",
        parse_mode="HTML",
    )


@router.message(SettingsStates.entering_analytics_query, F.text)
async def process_analytics_query(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer("⚠️ Слишком короткий запрос.")
        return

    await state.clear()
    await message.answer("📊 Анализирую...")

    stats = await hh.get_salary_statistics(query)

    if stats.get("count", 0) == 0:
        await message.answer(
            f"😔 По запросу «{query}» вакансий с зарплатой не найдено.",
            reply_markup=kb.main_menu_kb(message.from_user.id),
        )
        return

    text = (
        f"📊 <b>Аналитика: {query}</b>\n\n"
        f"📈 Всего: {stats['total_found']}\n"
        f"💰 С зарплатой: {stats['count']}\n\n"
        f"<b>Зарплаты (₽):</b>\n"
        f"├ Мин: {stats['min']:,}\n"
        f"├ Макс: {stats['max']:,}\n"
        f"├ Средняя: {stats['avg']:,}\n"
        f"└ Медиана: {stats['median']:,}\n"
    ).replace(",", " ")

    await message.answer(text, reply_markup=kb.main_menu_kb(message.from_user.id), parse_mode="HTML")


@router.message(SettingsStates.entering_analytics_query)
async def process_analytics_query_not_text(message: Message):
    await message.answer("⚠️ Введите запрос текстом.")
