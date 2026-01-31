from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb
from hh_api import hh
from config import config

router = Router()


class SettingsStates(StatesGroup):
    entering_analytics_query = State()
    adding_exclude_word = State()


# ==================== НАСТРОЙКИ ====================

@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
    user = await db.get_user(message.from_user.id)
    
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "Настройте параметры поиска:",
        reply_markup=kb.settings_kb(user),
        parse_mode="HTML"
    )


# ==================== МОИ ОТКЛИКИ ====================

@router.message(F.text == "📨 Мои отклики")
async def show_applications(message: Message):
    await message.answer(
        "📨 <b>Мои отклики</b>\n\n"
        "🚧 <i>Функция в разработке</i>\n\n"
        "Для откликов требуется интеграция с API HH.ru.\n"
        "Следите за обновлениями!",
        reply_markup=kb.main_menu_kb(message.from_user.id),
        parse_mode="HTML"
    )


# ==================== ПИСЬМА ====================

@router.message(F.text == "✉️ Письма")
async def show_letters(message: Message):
    await message.answer(
        "✉️ <b>Сопроводительные письма</b>\n\n"
        "🚧 <i>Функция в разработке</i>\n\n"
        "Скоро вы сможете создавать шаблоны писем.\n"
        "Следите за обновлениями!",
        reply_markup=kb.main_menu_kb(message.from_user.id),
        parse_mode="HTML"
    )



# ==================== ГОРОД ====================

@router.callback_query(F.data == "settings_city")
async def settings_city(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "📍 <b>Выберите город:</b>",
            reply_markup=kb.cities_kb(),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "settings_salary_toggle")
async def settings_salary_toggle(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    new_value = not (user.only_with_salary if user else False)
    
    await db.update_user_settings(callback.from_user.id, only_with_salary=new_value)
    user = await db.get_user(callback.from_user.id)
    
    try:
        await callback.message.edit_text(
            "⚙️ <b>Настройки</b>",
            reply_markup=kb.settings_kb(user),
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    await callback.answer(f"✅ {'Включено' if new_value else 'Выключено'}")


@router.callback_query(F.data == "settings_exclude")
async def settings_exclude(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    words = user.exclude_words if user else []
    
    text = "🚫 <b>Слова-исключения</b>\n\n"
    if words:
        text += ", ".join([f"<code>{w}</code>" for w in words])
    else:
        text += "Список пуст."
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=kb.settings_exclude_kb(words),
            parse_mode="HTML"
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
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer()


@router.message(SettingsStates.adding_exclude_word)
async def process_exclude_word(message: Message, state: FSMContext):
    word = message.text.strip().lower()
    
    # Игнорируем кнопки меню
    if message.text in config.MENU_BUTTONS:
        await state.clear()
        return
    
    if len(word) < 2:
        await message.answer("⚠️ Слишком короткое")
        return
    
    user = await db.get_user(message.from_user.id)
    words = user.exclude_words if user else []
    
    if word not in words:
        words.append(word)
        await db.update_user_settings(message.from_user.id, exclude_words=words)
    
    await state.clear()
    
    await message.answer(
        f"✅ Добавлено: <b>{word}</b>",
        reply_markup=kb.settings_exclude_kb(words),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("settings_remove_exclude_"))
async def settings_remove_exclude(callback: CallbackQuery):
    word = callback.data.replace("settings_remove_exclude_", "")
    
    user = await db.get_user(callback.from_user.id)
    words = user.exclude_words if user else []
    
    if word in words:
        words.remove(word)
        await db.update_user_settings(callback.from_user.id, exclude_words=words)
    
    try:
        await callback.message.edit_text(
            "🚫 <b>Слова-исключения</b>\n\n" +
            (", ".join([f"<code>{w}</code>" for w in words]) if words else "Список пуст."),
            reply_markup=kb.settings_exclude_kb(words),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer(f"✅ Удалено")


@router.callback_query(F.data == "settings_clear_exclude")
async def settings_clear_exclude(callback: CallbackQuery):
    await db.update_user_settings(callback.from_user.id, exclude_words=[])
    
    try:
        await callback.message.edit_text(
            "🚫 <b>Слова-исключения</b>\n\n✅ Очищено",
            reply_markup=kb.settings_exclude_kb([]),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer("🗑 Очищено")


@router.callback_query(F.data == "settings_reset")
async def settings_reset(callback: CallbackQuery):
    await db.update_user_settings(
        callback.from_user.id,
        city=None, city_name=None, experience=None,
        schedule=None, min_salary=None,
        only_with_salary=False, exclude_words=[]
    )
    
    user = await db.get_user(callback.from_user.id)
    
    try:
        await callback.message.edit_text(
            "⚙️ <b>Настройки</b>\n\n✅ Сброшено!",
            reply_markup=kb.settings_kb(user),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer("🔄 Сброшено")


@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    
    try:
        await callback.message.edit_text(
            "⚙️ <b>Настройки</b>",
            reply_markup=kb.settings_kb(user),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer()


# ==================== АНАЛИТИКА ====================

@router.message(F.text == "📊 Аналитика")
async def show_analytics_prompt(message: Message, state: FSMContext):
    await state.set_state(SettingsStates.entering_analytics_query)
    await message.answer(
        "📊 <b>Аналитика зарплат</b>\n\n"
        "Введите профессию:\n\n"
        "<i>Пример: Python разработчик</i>",
        parse_mode="HTML"
    )


@router.message(SettingsStates.entering_analytics_query)
async def process_analytics_query(message: Message, state: FSMContext):
    query = message.text.strip()
    
    # Игнорируем кнопки меню
    if query in config.MENU_BUTTONS:
        await state.clear()
        return
    
    await state.clear()
    await message.answer("📊 Анализирую...")
    
    stats = await hh.get_salary_statistics(query)
    
    if stats.get("count", 0) == 0:
        await message.answer(
            f"😔 По запросу «{query}» вакансий с зарплатой не найдено.",
            reply_markup=kb.main_menu_kb(message.from_user.id)
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
    
    await message.answer(text, reply_markup=kb.main_menu_kb(), parse_mode="HTML")

# Добавь в handlers/settings.py

@router.callback_query(F.data == "settings_notifications")
async def settings_notifications(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    enabled = user.notifications_enabled if user else True
    
    await callback.message.edit_text(
        "🔔 <b>Автоуведомления</b>\n\n"
        "Бот будет присылать новые вакансии по вашим подпискам автоматически.\n\n"
        f"Статус: {'✅ Включены' if enabled else '❌ Выключены'}",
        reply_markup=kb.notifications_kb(enabled),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    new_value = not (user.notifications_enabled if user else True)
    
    await db.update_user_settings(callback.from_user.id, notifications_enabled=new_value)
    
    await callback.message.edit_text(
        "🔔 <b>Автоуведомления</b>\n\n"
        f"{'✅ Уведомления включены!' if new_value else '❌ Уведомления выключены'}",
        reply_markup=kb.notifications_kb(new_value),
        parse_mode="HTML"
    )
    await callback.answer()

