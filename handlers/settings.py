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
    waiting_hh_code = State()


# ==================== НАСТРОЙКИ ====================

@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
    user = await db.get_user(message.from_user.id)
    is_authorized = bool(user and user.hh_access_token)
    
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "Настройте параметры поиска по умолчанию:",
        reply_markup=kb.settings_kb(user, is_authorized),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "settings_city")
async def settings_city(callback: CallbackQuery):
    await callback.message.edit_text(
        "📍 <b>Выберите город по умолчанию:</b>",
        reply_markup=kb.cities_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "settings_salary_toggle")
async def settings_salary_toggle(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    new_value = not (user.only_with_salary if user else False)
    
    await db.update_user_settings(
        callback.from_user.id,
        only_with_salary=new_value
    )
    
    user = await db.get_user(callback.from_user.id)
    is_authorized = bool(user and user.hh_access_token)
    
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "Настройте параметры поиска по умолчанию:",
        reply_markup=kb.settings_kb(user, is_authorized),
        parse_mode="HTML"
    )
    await callback.answer(f"✅ {'Включено' if new_value else 'Выключено'}")


@router.callback_query(F.data == "settings_exclude")
async def settings_exclude(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    words = user.exclude_words if user else []
    
    text = "🚫 <b>Слова-исключения</b>\n\n"
    if words:
        text += "Эти слова исключаются из поиска:\n"
        text += ", ".join([f"<code>{w}</code>" for w in words])
    else:
        text += "Список пуст."
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.settings_exclude_kb(words),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "settings_reset")
async def settings_reset(callback: CallbackQuery):
    await db.update_user_settings(
        callback.from_user.id,
        city=None,
        city_name=None,
        experience=None,
        schedule=None,
        min_salary=None,
        only_with_salary=False,
        exclude_words=[]
    )
    
    user = await db.get_user(callback.from_user.id)
    is_authorized = bool(user and user.hh_access_token)
    
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "✅ Настройки сброшены!",
        reply_markup=kb.settings_kb(user, is_authorized),
        parse_mode="HTML"
    )
    await callback.answer("🔄 Сброшено")


@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    is_authorized = bool(user and user.hh_access_token)
    
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>",
        reply_markup=kb.settings_kb(user, is_authorized),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== ПОДКЛЮЧЕНИЕ HH.RU ====================

@router.callback_query(F.data == "hh_connect")
async def hh_connect(callback: CallbackQuery, state: FSMContext):
    """Подключение аккаунта HH.ru"""
    
    if not config.HH_CLIENT_ID or config.HH_CLIENT_ID == "ВСТАВЬ_CLIENT_ID":
        await callback.answer("❌ OAuth не настроен", show_alert=True)
        return
    
    auth_url = hh.get_auth_url(state=str(callback.from_user.id))
    
    await state.set_state(SettingsStates.waiting_hh_code)
    
    await callback.message.edit_text(
        "🔗 <b>Подключение HH.ru</b>\n\n"
        "Для откликов нужно авторизоваться:\n\n"
        f"1️⃣ <a href='{auth_url}'>Нажмите здесь</a>\n"
        "2️⃣ Разрешите доступ\n"
        "3️⃣ Скопируйте <b>код</b> из адресной строки\n"
        "   (после <code>?code=</code>)\n"
        "4️⃣ Отправьте код мне\n\n"
        "<i>Пример кода: ABC123XYZ...</i>",
        reply_markup=kb.hh_connect_kb(),
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    await callback.answer()


@router.message(SettingsStates.waiting_hh_code)
async def process_hh_code(message: Message, state: FSMContext):
    """Обработка кода авторизации"""
    code = message.text.strip()
    
    if len(code) < 10:
        await message.answer("❌ Код слишком короткий. Попробуйте ещё раз.")
        return
    
    await message.answer("🔄 Проверяю код...")
    
    # Получаем токен
    token_data = await hh.get_access_token(code)
    
    if not token_data or "access_token" not in token_data:
        await message.answer(
            "❌ Не удалось получить токен.\n\n"
            "Попробуйте ещё раз или проверьте код.",
            reply_markup=kb.main_menu_kb()
        )
        await state.clear()
        return
    
    # Сохраняем токен
    await db.update_user_settings(
        message.from_user.id,
        hh_access_token=token_data["access_token"],
        hh_refresh_token=token_data.get("refresh_token"),
        hh_token_expires=str(token_data.get("expires_in", ""))
    )
    
    await state.clear()
    
    await message.answer(
        "✅ <b>Аккаунт HH.ru подключён!</b>\n\n"
        "Теперь вы можете:\n"
        "• Откликаться на вакансии\n"
        "• Просматривать статистику\n"
        "• Видеть свои резюме",
        reply_markup=kb.main_menu_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "hh_disconnect")
async def hh_disconnect(callback: CallbackQuery):
    """Отключение аккаунта HH.ru"""
    await db.update_user_settings(
        callback.from_user.id,
        hh_access_token=None,
        hh_refresh_token=None,
        hh_token_expires=None
    )
    
    user = await db.get_user(callback.from_user.id)
    
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "✅ Аккаунт HH.ru отключён",
        reply_markup=kb.settings_kb(user, False),
        parse_mode="HTML"
    )
    await callback.answer("✅ Отключено")


@router.callback_query(F.data == "hh_stats")
async def hh_stats(callback: CallbackQuery):
    """Статистика аккаунта HH.ru"""
    user = await db.get_user(callback.from_user.id)
    
    if not user or not user.hh_access_token:
        await callback.answer("❌ Сначала подключите HH.ru", show_alert=True)
        return
    
    await callback.message.edit_text("📊 Загружаю статистику...")
    
    # Получаем данные
    stats = await hh.get_user_stats(user.hh_access_token)
    resumes = await hh.get_my_resumes(user.hh_access_token)
    negotiations = await hh.get_negotiations(user.hh_access_token)
    
    # Считаем статистику откликов
    total_responses = len(negotiations)
    invitations = len([n for n in negotiations if n.get("state", {}).get("id") == "invitation"])
    discards = len([n for n in negotiations if n.get("state", {}).get("id") == "discard"])
    
    # Формируем текст
    text = "📊 <b>Статистика HH.ru</b>\n\n"
    
    # Резюме
    text += "📄 <b>Ваши резюме:</b>\n"
    if resumes:
        for r in resumes[:5]:
            title = r.get("title", "Без названия")
            views = r.get("total_views", 0)
            text += f"  • {title}\n"
            text += f"    👁 Просмотров: {views}\n"
    else:
        text += "  Нет резюме\n"
    
    text += f"\n📨 <b>Отклики:</b>\n"
    text += f"  • Всего отправлено: {total_responses}\n"
    text += f"  • 💼 Приглашений: {invitations}\n"
    text += f"  • ❌ Отказов: {discards}\n"
    
    if stats:
        text += f"\n📈 <b>Показы резюме:</b>\n"
        text += f"  • За неделю: {stats.get('views_7_days', 'н/д')}\n"
        text += f"  • За месяц: {stats.get('views_30_days', 'н/д')}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.hh_stats_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== АНАЛИТИКА ====================

@router.message(F.text == "📊 Аналитика")
async def show_analytics_prompt(message: Message, state: FSMContext):
    await state.set_state(SettingsStates.entering_analytics_query)
    await message.answer(
        "📊 <b>Аналитика зарплат</b>\n\n"
        "Введите профессию для анализа:\n\n"
        "<i>Пример: Python разработчик</i>",
        parse_mode="HTML"
    )


@router.message(SettingsStates.entering_analytics_query)
async def process_analytics_query(message: Message, state: FSMContext):
    query = message.text.strip()
    
    await state.clear()
    await message.answer("📊 Анализирую рынок...")
    
    stats = await hh.get_salary_statistics(query)
    
    if stats.get("count", 0) == 0:
        await message.answer(
            f"😔 По запросу «{query}» не найдено вакансий с зарплатой.",
            reply_markup=kb.main_menu_kb()
        )
        return
    
    text = (
        f"📊 <b>Аналитика: {query}</b>\n\n"
        f"📈 Всего вакансий: {stats['total_found']}\n"
        f"💰 С зарплатой: {stats['count']}\n\n"
        f"<b>Зарплаты (₽):</b>\n"
        f"├ Минимум: {stats['min']:,}\n"
        f"├ Максимум: {stats['max']:,}\n"
        f"├ Средняя: {stats['avg']:,}\n"
        f"└ Медиана: {stats['median']:,}\n"
    ).replace(",", " ")
    
    await message.answer(
        text,
        reply_markup=kb.main_menu_kb(),
        parse_mode="HTML"
    )


# ==================== ПОДДЕРЖКА ====================

@router.message(F.text == "💬 Поддержка")
async def show_support(message: Message):
    await message.answer(
        "💬 <b>Техническая поддержка</b>\n\n"
        "Если возникли вопросы или проблемы:\n\n"
        f"📩 Напишите: @{config.SUPPORT_USERNAME}\n\n"
        "<i>Обычно отвечаем в течение 24 часов</i>",
        reply_markup=kb.support_kb(),
        parse_mode="HTML"
    )
