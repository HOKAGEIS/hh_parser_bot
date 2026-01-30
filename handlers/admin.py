from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite

import database as db
import keyboards as kb
from config import config

router = Router()


class AdminStates(StatesGroup):
    waiting_broadcast = State()


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


# ==================== АДМИН ПАНЕЛЬ ====================

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
        
        cursor = await conn.execute("SELECT COUNT(*) FROM favorites")
        total_favs = (await cursor.fetchone())[0]
    
    await message.answer(
        "👑 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"🔔 Подписок: {total_subs}\n"
        f"⭐ В избранном: {total_favs}",
        reply_markup=kb.admin_kb(),
        parse_mode="HTML"
    )


# ==================== СТАТИСТИКА ====================

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    
    async with aiosqlite.connect(db.DATABASE) as conn:
        # Регистрации по дням
        cursor = await conn.execute("""
            SELECT DATE(created_at), COUNT(*) 
            FROM users 
            GROUP BY DATE(created_at) 
            ORDER BY DATE(created_at) DESC 
            LIMIT 7
        """)
        daily = await cursor.fetchall()
        
        # Всего пользователей
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        total = (await cursor.fetchone())[0]
        
        # Активных за сегодня (если есть поле last_active)
        cursor = await conn.execute("SELECT COUNT(*) FROM subscriptions WHERE active = 1")
        active_subs = (await cursor.fetchone())[0]
    
    text = "📊 <b>Статистика</b>\n\n"
    text += f"👥 Всего пользователей: {total}\n"
    text += f"🔔 Активных подписок: {active_subs}\n\n"
    text += "<b>Регистрации по дням:</b>\n"
    
    for date, count in daily:
        text += f"📅 {date}: +{count}\n"
    
    if not daily:
        text += "Нет данных\n"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=kb.admin_back_kb(),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer()


# ==================== РАССЫЛКА ====================

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    
    await state.set_state(AdminStates.waiting_broadcast)
    
    try:
        await callback.message.edit_text(
            "📢 <b>Рассылка</b>\n\n"
            "Отправьте сообщение для рассылки всем пользователям.\n\n"
            "⚠️ Для отмены напишите /cancel",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer()


@router.message(Command("cancel"), AdminStates.waiting_broadcast)
async def cancel_broadcast(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Рассылка отменена", reply_markup=kb.admin_kb())


@router.message(AdminStates.waiting_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    
    # Получаем всех пользователей
    async with aiosqlite.connect(db.DATABASE) as conn:
        cursor = await conn.execute("SELECT id FROM users")
        users = await cursor.fetchall()
    
    await message.answer(f"📤 Начинаю рассылку {len(users)} пользователям...")
    
    success = 0
    failed = 0
    
    from aiogram import Bot
    bot = Bot.get_current()
    
    for (user_id,) in users:
        try:
            await bot.send_message(
                user_id,
                message.text,
                parse_mode="HTML"
            )
            success += 1
        except Exception:
            failed += 1
    
    await message.answer(
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"📨 Отправлено: {success}\n"
        f"❌ Ошибок: {failed}",
        reply_markup=kb.admin_kb(),
        parse_mode="HTML"
    )


# ==================== НАЗАД ====================

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    async with aiosqlite.connect(db.DATABASE) as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        
        cursor = await conn.execute("SELECT COUNT(*) FROM subscriptions WHERE active = 1")
        total_subs = (await cursor.fetchone())[0]
        
        cursor = await conn.execute("SELECT COUNT(*) FROM favorites")
        total_favs = (await cursor.fetchone())[0]
    
    try:
        await callback.message.edit_text(
            "👑 <b>Админ-панель</b>\n\n"
            f"👥 Пользователей: {total_users}\n"
            f"🔔 Подписок: {total_subs}\n"
            f"⭐ В избранном: {total_favs}",
            reply_markup=kb.admin_kb(),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer()
