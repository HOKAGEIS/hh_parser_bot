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
    
    status = "включено" if new_value else "выключено"
    await callback.answer(f"✅ Показывать только с зарплатой: {status}")


@router.callback_query(F.data == "settings_exclude")
async def settings_exclude(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    words = user.exclude_words if user else []
    
    text = "🚫 <b>Слова-исключения (по умолчанию)</b>\n\n"
    if words:
        text += "Эти слова будут исключаться из всех поисков:\n"
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
        "Настройки сброшены!",
        reply_markup=kb.settings_kb(user, is_authorized),
        parse_mode="HTML"
    )
    await callback.answer("🔄 Настройки сброшены")


# ==================== ПОДКЛЮЧЕНИЕ HH.RU ====================

@router.callback_query(F.data == "hh_connect")
async def hh_connect(callback: CallbackQuery):
    """Подключение аккаунта HH.ru"""
    auth_url = hh.get_auth_url(state=str(callback.from_user.id))
    
    await callback.message.edit_text(
        "🔗 <b>Подключение HH.ru</b>\n\n"
        "Для откликов на вакансии нужно авторизоваться:\n\n"
        f"1. <a href='{auth_url}'>Нажмите здесь для авторизации</a>\n"
        "2. Разрешите доступ приложению\n"
        "3. Скопируйте код из адресной строки\n"
        "4. Отправьте код боту\n\n"
        "<i>Код будет в URL после ?code=...</i>",
        reply_markup=kb.hh_connect_kb(),
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    await callback.answer()


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
    await callback.answer("✅ HH.ru отключён")


@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    is_authorized = bool(user and user.hh_access_token)
    
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "Настройте параметры поиска по умолчанию:",
        reply_markup=kb.settings_kb(user, is_authorized),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== АНАЛИТИКА ====================

@router.message(F.text == "📊 Аналитика")
async def show_analytics_prompt(message: Message, state: FSMContext):
    await state.set_state(SettingsStates.entering_analytics_query)
    await message.answer(
        "📊 <b>Аналитика зарплат</b>\n\n"
        "Введите профессию для анализа зарплат на рынке:\n\n"
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
            f"😔 По запросу «{query}» не найдено вакансий с указанной зарплатой.",
            reply_markup=kb.main_menu_kb()
        )
        return
    
    text = (
        f"📊 <b>Аналитика: {query}</b>\n\n"
        f"📈 Всего вакансий: {stats['total_found']}\n"
        f"💰 С указанной зарплатой: {stats['count']}\n\n"
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
