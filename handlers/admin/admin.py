from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

import database as db
import keyboards as kb
from config import config

router = Router()

# Список админов (добавь свой Telegram ID)
ADMIN_IDS = [123456789]  # Замени на свой ID


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа")
        return
    
    # Получаем статистику
    async with db.aiosqlite.connect(db.DATABASE) as conn:
        # Всего пользователей
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        
        # Всего подписок
        cursor = await conn.execute("SELECT COUNT(*) FROM subscriptions WHERE active = 1")
        total_subs = (await cursor.fetchone())[0]
        
        # Всего откликов
        cursor = await conn.execute("SELECT COUNT(*) FROM applications")
        total_apps = (await cursor.fetchone())[0]
        
        # Всего избранного
        cursor = await conn.execute("SELECT COUNT(*) FROM favorites")
        total_favs = (await cursor.fetchone())[0]
    
    text = (
        "👑 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"🔔 Активных подписок: {total_subs}\n"
        f"📨 Откликов: {total_apps}\n"
        f"⭐ В избранном: {total_favs}\n"
    )
    
    await message.answer(text, reply_markup=kb.admin_kb(), parse_mode="HTML")


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\n"
        "Отправьте сообщение для рассылки всем пользователям:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    # Детальная статистика
    async with db.aiosqlite.connect(db.DATABASE) as conn:
        cursor = await conn.execute("""
            SELECT DATE(created_at), COUNT(*) 
            FROM users 
            GROUP BY DATE(created_at) 
            ORDER BY DATE(created_at) DESC 
            LIMIT 7
        """)
        daily_users = await cursor.fetchall()
    
    text = "📊 <b>Статистика по дням</b>\n\n"
    for date, count in daily_users:
        text += f"📅 {date}: +{count} польз.\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.admin_back_kb(),
        parse_mode="HTML"
    )
    await callback.answer()
