from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from hh_api import Vacancy

router = Router()


@router.message(F.text == "⭐ Избранное")
async def show_favorites(message: Message):
    favorites = await db.get_favorites(message.from_user.id)
    
    if not favorites:
        await message.answer(
            "📭 <b>Избранное пусто</b>\n\n"
            "Добавляйте вакансии в избранное при поиске, "
            "чтобы вернуться к ним позже.",
            parse_mode="HTML"
        )
        return
    
    await message.answer(
        f"⭐ <b>Избранное</b> ({len(favorites)} вакансий)\n\n"
        "Выберите вакансию:",
        reply_markup=kb.favorites_list_kb(favorites),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("show_fav_"))
async def show_favorite_vacancy(callback: CallbackQuery):
    vacancy_id = callback.data.replace("show_fav_", "")
    
    favorites = await db.get_favorites(callback.from_user.id)
    
    fav = None
    for f in favorites:
        if f.vacancy_id == vacancy_id:
            fav = f
            break
    
    if not fav:
        await callback.answer("Вакансия не найдена")
        return
    
    v = fav.vacancy_data
    
    # Формируем сообщение
    salary_text = "💰 Зарплата не указана"
    if v.get("salary_from") or v.get("salary_to"):
        currency = {"RUR": "₽", "USD": "$", "EUR": "€"}.get(v.get("salary_currency"), "")
        if v.get("salary_from") and v.get("salary_to"):
            salary_text = f"💰 {v['salary_from']:,} - {v['salary_to']:,} {currency}".replace(",", " ")
        elif v.get("salary_from"):
            salary_text = f"💰 от {v['salary_from']:,} {currency}".replace(",", " ")
        else:
            salary_text = f"💰 до {v['salary_to']:,} {currency}".replace(",", " ")
    
    text = (
        f"📌 <b>{v.get('name', 'Вакансия')}</b>\n\n"
        f"🏢 {v.get('employer', 'Не указано')}\n"
        f"📍 {v.get('city', 'Не указан')}\n"
        f"{salary_text}\n"
        f"📋 Опыт: {v.get('experience', 'Не указан')}\n\n"
        f"🔗 <a href='{v.get('url', '')}'>Открыть на hh.ru</a>"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.favorite_item_kb(vacancy_id),
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    await callback.answer()


@router.callback_query(F.data.startswith("del_fav_"))
async def delete_favorite(callback: CallbackQuery):
    vacancy_id = callback.data.replace("del_fav_", "")
    
    await db.remove_favorite(callback.from_user.id, vacancy_id)
    
    # Обновляем список
    favorites = await db.get_favorites(callback.from_user.id)
    
    if not favorites:
        await callback.message.edit_text(
            "📭 <b>Избранное пусто</b>",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"⭐ <b>Избранное</b> ({len(favorites)} вакансий)\n\n"
            "Выберите вакансию:",
            reply_markup=kb.favorites_list_kb(favorites),
            parse_mode="HTML"
        )
    
    await callback.answer("💔 Удалено из избранного")


@router.callback_query(F.data == "back_to_favorites")
async def back_to_favorites(callback: CallbackQuery):
    favorites = await db.get_favorites(callback.from_user.id)
    
    if not favorites:
        await callback.message.edit_text(
            "📭 <b>Избранное пусто</b>",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"⭐ <b>Избранное</b> ({len(favorites)} вакансий)\n\n"
            "Выберите вакансию:",
            reply_markup=kb.favorites_list_kb(favorites),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data == "clear_favorites")
async def clear_favorites_confirm(callback: CallbackQuery):
    await callback.message.edit_text(
        "🗑 <b>Очистить избранное?</b>\n\n"
        "Все сохранённые вакансии будут удалены.",
        reply_markup=kb.confirm_kb("clear_favs"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_clear_favs")
async def confirm_clear_favorites(callback: CallbackQuery):
    favorites = await db.get_favorites(callback.from_user.id)
    for fav in favorites:
        await db.remove_favorite(callback.from_user.id, fav.vacancy_id)
    
    await callback.message.edit_text(
        "✅ Избранное очищено",
        parse_mode="HTML"
    )
    await callback.answer()
