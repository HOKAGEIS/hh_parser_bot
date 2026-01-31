# handlers/admin.py (исправленный код)
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import sqlite3  # Заменен aiosqlite на sqlite3

import database as db
import keyboards as kb
from config import Config  # Заменено config на Config

router = Router()


class AdminStates(StatesGroup):
    waiting_broadcast = State()


def is_admin(user_id: int) -> bool:
    return user_id in Config.ADMIN_IDS  # Заменено config на Config


# ==================== ПАНЕЛЬ ====================

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    conn = sqlite3.connect(db.Config.DATABASE_PATH)  # Заменено db.DATABASE на db.Config.DATABASE_PATH
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE is_active = 1")  # Заменено active на is_active
    total_subs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM favorites")
    total_favs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'open'")  # Предполагается наличие таблицы tickets
    open_tickets = cursor.fetchone()[0]
    
    conn.close()
    
    await message.answer(
        "👑 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"🔔 Подписок: {total_subs}\n"
        f"⭐ В избранном: {total_favs}\n"
        f"📬 Открытых тикетов: {open_tickets}",
        reply_markup=kb.admin_kb(),
        parse_mode="HTML"
    )

@router.message(F.text == "👑 Админ-панель")
async def admin_panel_button(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    conn = sqlite3.connect(db.Config.DATABASE_PATH)  # Заменено db.DATABASE на db.Config.DATABASE_PATH
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE is_active = 1")  # Заменено active на is_active
    total_subs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM favorites")
    total_favs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'open'")  # Предполагается наличие таблицы tickets
    open_tickets = cursor.fetchone()[0]
    
    conn.close()
    
    await message.answer(
        "👑 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"🔔 Подписок: {total_subs}\n"
        f"⭐ В избранном: {total_favs}\n"
        f"📬 Открытых тикетов: {open_tickets}",
        reply_markup=kb.admin_kb(),
        parse_mode="HTML"
    )

# ==================== СТАТИСТИКА ====================

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    
    conn = sqlite3.connect(db.Config.DATABASE_PATH)  # Заменено db.DATABASE на db.Config.DATABASE_PATH
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DATE(created_at), COUNT(*) 
        FROM users 
        GROUP BY DATE(created_at) 
        ORDER BY DATE(created_at) DESC 
        LIMIT 7
    """)
    daily = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    
    conn.close()
    
    text = "📊 <b>Статистика</b>\n\n"
    text += f"👥 Всего пользователей: {total}\n\n"
    text += "<b>Регистрации по дням:</b>\n"
    
    if daily:
        for date, count in daily:
            text += f"📅 {date}: +{count}\n"
    else:
        text += "Нет данных\n"
    
    try:
        await callback.message.edit_text(text, reply_markup=kb.admin_back_kb(), parse_mode="HTML")
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
        await callback.message.answer(
            "📢 <b>Рассылка</b>\n\n"
            "Отправьте сообщение для рассылки.\n\n"
            "⚠️ Для отмены: /cancel",
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.message(Command("cancel"))
async def cancel_any(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=kb.main_menu_kb())


@router.message(AdminStates.waiting_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    # Игнорируем команды
    if message.text and message.text.startswith("/"):
        return
    
    await state.clear()
    
    # Получаем пользователей
    conn = sqlite3.connect(db.Config.DATABASE_PATH)  # Заменено db.DATABASE на db.Config.DATABASE_PATH
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users")
    users = cursor.fetchall()
    
    conn.close()
    
    status_msg = await message.answer(f"📤 Рассылка {len(users)} пользователям...")
    
    success = 0
    failed = 0
    
    for (user_id,) in users:
        try:
            await bot.send_message(user_id, message.text, parse_mode="HTML")
            success += 1
        except Exception:
            failed += 1
    
    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"📨 Отправлено: {success}\n"
        f"❌ Ошибок: {failed}",
        parse_mode="HTML"
    )
    
    await message.answer("👑 Админ-панель", reply_markup=kb.admin_kb())


# ==================== ТИКЕТЫ ====================

@router.callback_query(F.data == "admin_tickets")
async def admin_tickets(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    
    tickets = db.get_all_open_tickets()  # Убран await
    
    if not tickets:
        try:
            await callback.message.edit_text(
                "📭 Нет открытых обращений",
                reply_markup=kb.admin_back_kb(),
                parse_mode="HTML"
            )
        except Exception:
            pass
    else:
        text = f"📬 <b>Открытые обращения ({len(tickets)})</b>\n\n"
        for t in tickets[:10]:
            username = f"@{t['username']}" if t['username'] else f"ID: {t['user_id']}"
            text += f"• #{t['id']} от {username}\n"
        
        try:
            await callback.message.edit_text(
                text,
                reply_markup=kb.admin_tickets_list_kb(tickets),
                parse_mode="HTML"
            )
        except Exception:
            pass
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_view_ticket_"))
async def admin_view_ticket(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    ticket_id = int(callback.data.replace("admin_view_ticket_", ""))
    ticket = db.get_ticket_by_id(ticket_id)  # Убран await
    
    if not ticket:
        await callback.answer("Тикет не найден")
        return
    
    messages = db.get_ticket_messages(ticket_id)  # Убран await
    
    username = f"@{ticket['username']}" if ticket['username'] else f"ID: {ticket['user_id']}"
    text = f"📬 <b>Тикет #{ticket_id}</b>\n👤 {username}\n\n"
    
    for msg in messages[-10:]:
        sender = "👤 Пользователь" if msg["sender_type"] == "user" else "👨‍💼 Поддержка"
        text += f"<b>{sender}:</b>\n{msg['message']}\n\n"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=kb.admin_ticket_kb(ticket_id),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("admin_reply_"))
async def admin_reply_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    ticket_id = int(callback.data.replace("admin_reply_", ""))
    
    # Импортируем состояние из support
    from handlers.support import SupportStates
    
    await state.update_data(reply_ticket_id=ticket_id)
    await state.set_state(SupportStates.admin_replying)
    
    try:
        await callback.message.edit_text(
            f"✏️ <b>Ответ на тикет #{ticket_id}</b>\n\nНапишите ваш ответ:",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("admin_close_ticket_"))
async def admin_close_ticket(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    
    ticket_id = int(callback.data.replace("admin_close_ticket_", ""))
    ticket = db.get_ticket_by_id(ticket_id)  # Убран await
    
    db.close_ticket(ticket_id)  # Убран await
    
    try:
        await callback.message.edit_text(
            f"✅ Тикет #{ticket_id} закрыт",
            reply_markup=kb.admin_back_kb(),
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    # Уведомляем пользователя
    if ticket:
        try:
            await bot.send_message(
                ticket["user_id"],
                f"✅ Ваше обращение #{ticket_id} закрыто.",
                parse_mode="HTML"
            )
        except Exception:
            pass
    
    await callback.answer("Тикет закрыт")


# ==================== НАЗАД ====================

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    conn = sqlite3.connect(db.Config.DATABASE_PATH)  # Заменено db.DATABASE на db.Config.DATABASE_PATH
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'open'")  # Предполагается наличие таблицы tickets
    open_tickets = cursor.fetchone()[0]
    
    conn.close()
    
    try:
        await callback.message.edit_text(
            "👑 <b>Админ-панель</b>\n\n"
            f"👥 Пользователей: {total_users}\n"
            f"📬 Открытых тикетов: {open_tickets}",
            reply_markup=kb.admin_kb(),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer()
