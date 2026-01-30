from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb
from hh_api import hh

router = Router()


class ApplyStates(StatesGroup):
    writing_letter = State()
    selecting_resume = State()


@router.message(F.text == "📨 Мои отклики")
async def show_applications(message: Message):
    applications = await db.get_applications(message.from_user.id)
    
    if not applications:
        await message.answer(
            "📨 <b>Мои отклики</b>\n\n"
            "У вас пока нет откликов.\n\n"
            "Чтобы откликаться на вакансии:\n"
            "1. Подключите аккаунт HH.ru в ⚙️ Настройки\n"
            "2. Найдите вакансию\n"
            "3. Нажмите «Откликнуться»",
            parse_mode="HTML"
        )
        return
    
    text = "📨 <b>Мои отклики</b>\n\n"
    for app in applications[:15]:
        text += f"• <b>{app['vacancy_name'][:40]}</b>\n"
        text += f"  🏢 {app['employer']}\n"
        text += f"  📅 {app['applied_at'][:10]}\n\n"
    
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("apply_"))
async def start_apply(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.replace("apply_", "")
    
    user = await db.get_user(callback.from_user.id)
    
    if not user or not user.hh_access_token:
        await callback.answer(
            "⚠️ Подключите аккаунт HH.ru в настройках",
            show_alert=True
        )
        return
    
    # Получаем резюме
    resumes = await hh.get_my_resumes(user.hh_access_token)
    
    if not resumes:
        await callback.answer(
            "⚠️ У вас нет резюме на HH.ru",
            show_alert=True
        )
        return
    
    await state.update_data(vacancy_id=vacancy_id, resumes=resumes)
    
    # Получаем шаблоны писем
    letters = await db.get_cover_letters(callback.from_user.id)
    
    await callback.message.edit_text(
        "📨 <b>Отклик на вакансию</b>\n\n"
        "Выберите способ отправки:",
        reply_markup=kb.apply_kb(vacancy_id, letters),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("apply_template_"))
async def show_templates(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.replace("apply_template_", "")
    
    letters = await db.get_cover_letters(callback.from_user.id)
    
    await callback.message.edit_text(
        "📝 <b>Выберите шаблон письма:</b>",
        reply_markup=kb.letter_templates_kb(vacancy_id, letters),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("apply_write_"))
async def write_letter(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.replace("apply_write_", "")
    
    await state.update_data(vacancy_id=vacancy_id)
    await state.set_state(ApplyStates.writing_letter)
    
    await callback.message.edit_text(
        "✏️ <b>Напишите сопроводительное письмо:</b>\n\n"
        "<i>Расскажите о себе и почему вы подходите на эту позицию</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(ApplyStates.writing_letter)
async def process_letter(message: Message, state: FSMContext):
    letter_text = message.text.strip()
    
    if len(letter_text) < 10:
        await message.answer("⚠️ Письмо слишком короткое")
        return
    
    await state.update_data(letter=letter_text)
    data = await state.get_data()
    
    # Показываем выбор резюме
    resumes = data.get("resumes", [])
    vacancy_id = data.get("vacancy_id")
    
    await state.set_state(ApplyStates.selecting_resume)
    
    await message.answer(
        "📄 <b>Выберите резюме:</b>",
        reply_markup=kb.resumes_kb(resumes, vacancy_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("apply_now_"))
async def apply_now(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.replace("apply_now_", "").split("_")
    vacancy_id = parts[0]
    letter_type = parts[1] if len(parts) > 1 else "none"
    
    data = await state.get_data()
    resumes = data.get("resumes", [])
    
    if not resumes:
        user = await db.get_user(callback.from_user.id)
        resumes = await hh.get_my_resumes(user.hh_access_token)
        await state.update_data(resumes=resumes)
    
    await state.update_data(vacancy_id=vacancy_id, letter="" if letter_type == "none" else data.get("letter", ""))
    await state.set_state(ApplyStates.selecting_resume)
    
    await callback.message.edit_text(
        "📄 <b>Выберите резюме для отклика:</b>",
        reply_markup=kb.resumes_kb(resumes, vacancy_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("use_letter_"))
async def use_letter_template(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.replace("use_letter_", "").split("_")
    vacancy_id = parts[0]
    letter_id = int(parts[1])
    
    letter = await db.get_cover_letter(letter_id, callback.from_user.id)
    
    if letter:
        await state.update_data(letter=letter["text"], vacancy_id=vacancy_id)
    
    data = await state.get_data()
    resumes = data.get("resumes", [])
    
    if not resumes:
        user = await db.get_user(callback.from_user.id)
        resumes = await hh.get_my_resumes(user.hh_access_token)
        await state.update_data(resumes=resumes)
    
    await state.set_state(ApplyStates.selecting_resume)
    
    await callback.message.edit_text(
        f"✅ Письмо: <b>{letter['name']}</b>\n\n"
        "📄 <b>Выберите резюме:</b>",
        reply_markup=kb.resumes_kb(resumes, vacancy_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("resume_"))
async def select_resume_and_apply(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.replace("resume_", "").split("_")
    vacancy_id = parts[0]
    resume_id = parts[1]
    
    data = await state.get_data()
    letter = data.get("letter", "")
    
    user = await db.get_user(callback.from_user.id)
    
    if not user or not user.hh_access_token:
        await callback.answer("⚠️ Ошибка авторизации", show_alert=True)
        return
    
    await callback.message.edit_text("📨 Отправляю отклик...")
    
    # Отправляем отклик
    result = await hh.apply_to_vacancy(
        vacancy_id=vacancy_id,
        resume_id=resume_id,
        access_token=user.hh_access_token,
        message=letter
    )
    
    if result.get("status") in [200, 201, 303]:
        # Сохраняем в историю
        vacancies = data.get("vacancies", [])
        vacancy_name = "Вакансия"
        employer = "Компания"
        for v in vacancies:
            if v.get("id") == vacancy_id:
                vacancy_name = v.get("name", "Вакансия")
                employer = v.get("employer", "Компания")
                break
        
        await db.add_application(callback.from_user.id, vacancy_id, vacancy_name, employer)
        
        await callback.message.edit_text(
            "✅ <b>Отклик отправлен!</b>\n\n"
            "Работодатель увидит ваше резюме и сопроводительное письмо.\n\n"
            "Удачи! 🍀",
            parse_mode="HTML"
        )
    else:
        error_text = result.get("data", "Неизвестная ошибка")
        await callback.message.edit_text(
            f"❌ <b>Ошибка при отправке</b>\n\n"
            f"Возможно, вы уже откликались на эту вакансию.\n\n"
            f"<code>{error_text[:200]}</code>",
            parse_mode="HTML"
        )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "already_applied")
async def already_applied(callback: CallbackQuery):
    await callback.answer("✅ Вы уже откликнулись на эту вакансию", show_alert=True)
