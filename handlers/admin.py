from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import aiosqlite

import database as db
import keyboards as kb
from config import config

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    async with aiosqlite.connect(db.DATABASE) as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        
        cursor = await conn.execute("SELECT COUNT(*) FROM subscriptions WHERE active = 1")
        total_subs = (await cursor.fetchone())[0]
        
        cursor = await conn.execute("SELECT COUNT(*) FROM applications")
        total_apps = (await cursor.fetchone())[0]
        
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


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    async with aiosqlite.connect(db.DATABASE) as conn:
        cursor = await conn.execute("""
            SELECT DATE(created_at), COUNT(*) 
            FROM users 
            GROUP BY DATE(created_at) 
            ORDER BY DATE(created_at) DESC 
            LIMIT 7
        """)
        daily = await cursor.fetchall()
    
    text = "📊 <b>Статистика по дням</b>\n\n"
    for date, count in daily:
        text += f"📅 {date}: +{count}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.admin_back_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    # Возврат в админку
    async with aiosqlite.connect(db.DATABASE) as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
    
    await callback.message.edit_text(
        f"👑 <b>Админ-панель</b>\n\n👥 Пользователей: {total_users}",
        reply_markup=kb.admin_kb(),
        parse_mode="HTML"
    )
    await callback.answer()
