from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

import database as db
import keyboards as kb
from config import config

router = Router()


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
    user = await db.get_user(message.from_user.id)
    
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "Настройте параметры поиска по умолчанию:",
        reply_markup=kb.settings_kb(user),
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
    
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "Настройте параметры поиска по умолчанию:",
        reply_markup=kb.settings_kb(user),
        parse_mode="HTML"
    )
    
    status = "включено" if new_value else "выключено"
    await callback.answer(f"✅ Показывать только с зарплатой: {status}")


@router.callback_query(F.data == "settings_reset")
async def settings_reset(callback: CallbackQuery):
    await db.update_user_settings(
        callback.from_user.id,
        city=None,
        experience=None,
        schedule=None,
        min_salary=None,
        only_with_salary=False
    )
    
    user = await db.get_user(callback.from_user.id)
    
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "Настройки сброшены!",
        reply_markup=kb.settings_kb(user),
        parse_mode="HTML"
    )
    await callback.answer("🔄 Настройки сброшены")


# ==================== АНАЛИТИКА ====================

@router.message(F.text == "📊 Аналитика")
async def show_analytics_prompt(message: Message):
    await message.answer(
        "📊 <b>Аналитика зарплат</b>\n\n"
        "Введите профессию для анализа зарплат на рынке:\n\n"
        "<i>Пример: Python разработчик</i>",
        parse_mode="HTML"
    )


@router.message(F.text.regexp(r"^[^/🔍⭐🔔📊⚙️]"))  # Не команда и не кнопка
async def process_analytics_query(message: Message):
    # Проверяем, не из главного меню ли это
    if message.text in ["🔍 Поиск вакансий", "⭐ Избранное", "🔔 Подписки", "📊 Аналитика", "⚙️ Настройки"]:
        return
    
    query = message.text.strip()
    
    await message.answer("📊 Анализирую рынок...")
    
    from hh_api import hh
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
