from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb
from config import config

router = Router()


class SupportStates(StatesGroup):
    writing_message = State()
    admin_replying = State()


# ==================== ПОЛЬЗОВАТЕЛЬ ====================

@router.message(F.text == "💬 Поддержка")
async def show_support(message: Message):
    ticket = await db.get_open_ticket(message.from_user.id)
    
    if ticket:
        messages = await db.get_ticket_messages(ticket["id"])
        
        text = f"💬 <b>Обращение #{ticket['id']}</b>\n\n"
        
        for msg in messages[-5:]:
            sender = "👤 Вы" if msg["sender_type"] == "user" else "👨‍💼 Поддержка"
            text += f"{sender}:\n{msg['message']}\n\n"
        
        await message.answer(text, reply_markup=kb.support_ticket_kb(ticket["id"]), parse_mode="HTML")
    else:
        await message.answer(
            "💬 <b>Техническая поддержка</b>\n\n"
            "Нажмите кнопку ниже, чтобы создать обращение:",
            reply_markup=kb.support_menu_kb(),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "create_ticket")
async def create_ticket(callback: CallbackQuery, state: FSMContext):
    existing = await db.get_open_ticket(callback.from_user.id)
    if existing:
        await callback.answer("У вас уже есть открытое обращение", show_alert=True)
        return
    
    await state.set_state(SupportStates.writing_message)
    
    await callback.message.edit_text(
        "💬 <b>Новое обращение</b>\n\nОпишите вашу проблему:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SupportStates.writing_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    if message.text in config.MENU_BUTTONS:
        await state.clear()
        return
    
    user_message = message.text.strip()
    
    if len(user_message) < 5:
        await message.answer("⚠️ Сообщение слишком короткое")
        return
    
    data = await state.get_data()
    ticket_id = data.get("ticket_id")
    
    if not ticket_id:
        ticket_id = await db.create_ticket(message.from_user.id, message.from_user.username)
    
    await db.add_ticket_message(ticket_id, "user", user_message)
    await state.clear()
    
    await message.answer(
        f"✅ <b>Обращение #{ticket_id}</b>\n\nМы получили ваше сообщение!",
        reply_markup=kb.main_menu_kb(),
        parse_mode="HTML"
    )
    
    # Уведомляем админов
    for admin_id in config.ADMIN_IDS:
        try:
            username = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
            await bot.send_message(
                admin_id,
                f"🆕 <b>Новое обращение #{ticket_id}</b>\n\n👤 От: {username}\n\n💬 {user_message}",
                reply_markup=kb.admin_ticket_kb(ticket_id),
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("continue_ticket_"))
async def continue_ticket(callback: CallbackQuery, state: FSMContext):
    ticket_id = int(callback.data.replace("continue_ticket_", ""))
    await state.update_data(ticket_id=ticket_id)
    await state.set_state(SupportStates.writing_message)
    
    await callback.message.edit_text("💬 Напишите сообщение:")
    await callback.answer()


@router.callback_query(F.data.startswith("close_my_ticket_"))
async def close_my_ticket(callback: CallbackQuery):
    ticket_id = int(callback.data.replace("close_my_ticket_", ""))
    await db.close_ticket(ticket_id)
    
    await callback.message.edit_text(f"✅ Обращение #{ticket_id} закрыто.")
    await callback.answer()


# ==================== АДМИН ====================

@router.callback_query(F.data == "admin_tickets")
async def admin_tickets(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    tickets = await db.get_all_open_tickets()
    
    if not tickets:
        await callback.message.edit_text("📭 Нет открытых обращений", reply_markup=kb.admin_back_kb())
    else:
        text = f"📬 <b>Открытые обращения ({len(tickets)})</b>\n\n"
        await callback.message.edit_text(text, reply_markup=kb.admin_tickets_list_kb(tickets), parse_mode="HTML")
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_view_ticket_"))
async def admin_view_ticket(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    ticket_id = int(callback.data.replace("admin_view_ticket_", ""))
    ticket = await db.get_ticket_by_id(ticket_id)
    
    if not ticket:
        await callback.answer("Тикет не найден")
        return
    
    messages = await db.get_ticket_messages(ticket_id)
    
    username = f"@{ticket['username']}" if ticket['username'] else f"ID: {ticket['user_id']}"
    text = f"📬 <b>Тикет #{ticket_id}</b>\n👤 {username}\n\n"
    
    for msg in messages:
        sender = "👤" if msg["sender_type"] == "user" else "👨‍💼"
        text += f"{sender} {msg['message']}\n\n"
    
    await callback.message.edit_text(text, reply_markup=kb.admin_ticket_kb(ticket_id), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_reply_"))
async def admin_reply_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    ticket_id = int(callback.data.replace("admin_reply_", ""))
    await state.update_data(reply_ticket_id=ticket_id)
    await state.set_state(SupportStates.admin_replying)
    
    await callback.message.edit_text(f"✏️ Ответ на тикет #{ticket_id}\n\nНапишите ответ:")
    await callback.answer()


@router.message(SupportStates.admin_replying)
async def process_admin_reply(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    data = await state.get_data()
    ticket_id = data.get("reply_ticket_id")
    
    if not ticket_id:
        await state.clear()
        return
    
    await db.add_ticket_message(ticket_id, "admin", message.text)
    await state.clear()
    
    ticket = await db.get_ticket_by_id(ticket_id)
    
    await message.answer(f"✅ Ответ отправлен в тикет #{ticket_id}", reply_markup=kb.admin_kb())
    
    # Уведомляем пользователя
    if ticket:
        try:
            await bot.send_message(
                ticket["user_id"],
                f"💬 <b>Ответ на обращение #{ticket_id}</b>\n\n👨‍💼 Поддержка:\n{message.text}",
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("admin_close_ticket_"))
async def admin_close_ticket(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    ticket_id = int(callback.data.replace("admin_close_ticket_", ""))
    ticket = await db.get_ticket_by_id(ticket_id)
    
    await db.close_ticket(ticket_id)
    
    await callback.message.edit_text(f"✅ Тикет #{ticket_id} закрыт", reply_markup=kb.admin_back_kb())
    
    if ticket:
        try:
            await bot.send_message(ticket["user_id"], f"✅ Обращение #{ticket_id} закрыто.")
        except Exception:
            pass
    
    await callback.answer()
