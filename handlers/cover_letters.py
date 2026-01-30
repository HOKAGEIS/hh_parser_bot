from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb

router = Router()


class LetterStates(StatesGroup):
    entering_name = State()
    entering_text = State()
    editing_text = State()


@router.message(F.text == "✉️ Письма")
async def show_letters(message: Message):
    letters = await db.get_cover_letters(message.from_user.id)
    
    text = "✉️ <b>Сопроводительные письма</b>\n\n"
    
    if letters:
        text += "Ваши шаблоны:\n\n"
        for letter in letters:
            prefix = "⭐ " if letter["is_default"] else ""
            text += f"{prefix}<b>{letter['name']}</b>\n"
    else:
        text += (
            "У вас пока нет шаблонов.\n\n"
            "Создайте шаблоны писем, чтобы быстро откликаться на вакансии."
        )
    
    await message.answer(
        text,
        reply_markup=kb.cover_letters_menu_kb(letters),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "create_letter")
async def create_letter(callback: CallbackQuery, state: FSMContext):
    await state.set_state(LetterStates.entering_name)
    
    await callback.message.edit_text(
        "✏️ <b>Создание шаблона</b>\n\n"
        "Введите название шаблона:\n\n"
        "<i>Например: Для IT вакансий, Стандартное, Для junior</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(LetterStates.entering_name)
async def process_letter_name(message: Message, state: FSMContext):
    name = message.text.strip()[:50]
    
    await state.update_data(letter_name=name)
    await state.set_state(LetterStates.entering_text)
    
    await message.answer(
        f"📝 Шаблон: <b>{name}</b>\n\n"
        "Теперь введите текст сопроводительного письма:\n\n"
        "<i>Совет: напишите универсальный текст, который подойдёт для разных вакансий</i>",
        parse_mode="HTML"
    )


@router.message(LetterStates.entering_text)
async def process_letter_text(message: Message, state: FSMContext):
    text = message.text.strip()
    
    if len(text) < 20:
        await message.answer("⚠️ Письмо слишком короткое (минимум 20 символов)")
        return
    
    data = await state.get_data()
    name = data.get("letter_name", "Шаблон")
    
    # Проверяем, первое ли это письмо
    existing = await db.get_cover_letters(message.from_user.id)
    is_default = len(existing) == 0
    
    await db.add_cover_letter(message.from_user.id, name, text, is_default)
    await state.clear()
    
    letters = await db.get_cover_letters(message.from_user.id)
    
    await message.answer(
        f"✅ Шаблон <b>{name}</b> создан!\n\n"
        + ("⭐ Установлен как основной" if is_default else ""),
        reply_markup=kb.cover_letters_menu_kb(letters),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("view_letter_"))
async def view_letter(callback: CallbackQuery):
    letter_id = int(callback.data.replace("view_letter_", ""))
    
    letter = await db.get_cover_letter(letter_id, callback.from_user.id)
    
    if not letter:
        await callback.answer("Письмо не найдено")
        return
    
    text = letter["text"]
    if len(text) > 500:
        text = text[:500] + "..."
    
    status = "⭐ Основной шаблон" if letter["is_default"] else ""
    
    await callback.message.edit_text(
        f"✉️ <b>{letter['name']}</b>\n"
        f"{status}\n\n"
        f"{text}",
        reply_markup=kb.cover_letter_kb(letter_id, letter["is_default"]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("default_letter_"))
async def set_default_letter(callback: CallbackQuery):
    letter_id = int(callback.data.replace("default_letter_", ""))
    
    await db.set_default_cover_letter(letter_id, callback.from_user.id)
    
    letter = await db.get_cover_letter(letter_id, callback.from_user.id)
    
    await callback.message.edit_text(
        f"⭐ <b>{letter['name']}</b>\n"
        "Установлен как основной шаблон\n\n"
        f"{letter['text'][:500]}",
        reply_markup=kb.cover_letter_kb(letter_id, True),
        parse_mode="HTML"
    )
    await callback.answer("⭐ Установлен как основной")


@router.callback_query(F.data.startswith("delete_letter_"))
async def delete_letter(callback: CallbackQuery):
    letter_id = int(callback.data.replace("delete_letter_", ""))
    
    await db.delete_cover_letter(letter_id, callback.from_user.id)
    
    letters = await db.get_cover_letters(callback.from_user.id)
    
    await callback.message.edit_text(
        "🗑 Шаблон удалён\n\n"
        "✉️ <b>Ваши шаблоны:</b>",
        reply_markup=kb.cover_letters_menu_kb(letters),
        parse_mode="HTML"
    )
    await callback.answer("🗑 Удалено")


@router.callback_query(F.data == "back_to_letters")
async def back_to_letters(callback: CallbackQuery):
    letters = await db.get_cover_letters(callback.from_user.id)
    
    await callback.message.edit_text(
        "✉️ <b>Сопроводительные письма</b>",
        reply_markup=kb.cover_letters_menu_kb(letters),
        parse_mode="HTML"
    )
    await callback.answer()
