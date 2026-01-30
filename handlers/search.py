from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb
from hh_api import hh, Vacancy
from config import config

router = Router()


class SearchStates(StatesGroup):
    entering_query = State()
    viewing_results = State()
    entering_city = State()
    entering_salary = State()
    entering_exclude_word = State()
    writing_cover_letter = State()


# ==================== НАЧАЛО ПОИСКА ====================

@router.message(F.text == "🔍 Поиск вакансий")
async def start_search(message: Message, state: FSMContext):
    await state.clear()
    
    await state.set_state(SearchStates.entering_query)
    await message.answer(
        "🔍 <b>Поиск вакансий</b>\n\n"
        "Введите название профессии или ключевые слова:\n\n"
        "<i>Примеры:\n"
        "• Python разработчик\n"
        "• Менеджер по продажам\n"
        "• UX/UI дизайнер</i>",
        parse_mode="HTML"
    )


@router.message(SearchStates.entering_query)
async def process_search_query(message: Message, state: FSMContext):
    query = message.text.strip()
    
    if len(query) < 2:
        await message.answer("⚠️ Запрос слишком короткий. Минимум 2 символа.")
        return
    
    user = await db.get_user(message.from_user.id)
    
    await state.update_data(
        query=query,
        city=user.default_city if user else None,
        city_name=user.default_city_name if user else None,
        experience=user.default_experience if user else None,
        schedule=user.default_schedule if user else None,
        salary=user.min_salary if user else None,
        only_with_salary=user.only_with_salary if user else False,
        exclude_words=user.exclude_words if user else [],
        page=0
    )
    
    data = await state.get_data()
    
    await message.answer(
        f"🔍 Запрос: <b>{query}</b>\n\n"
        "Настройте фильтры или сразу начните поиск:",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML"
    )


# ==================== ФИЛЬТРЫ ====================

@router.callback_query(F.data == "back_to_filters")
async def back_to_filters(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{data.get('query')}</b>\n\n"
        "Настройте фильтры:",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== ГОРОД ====================

@router.callback_query(F.data == "filter_city")
async def filter_city(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📍 <b>Выберите город</b>\n\n"
        "Выберите из списка или введите вручную:",
        reply_markup=kb.cities_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "enter_city_manual")
async def enter_city_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.entering_city)
    
    await callback.message.edit_text(
        "📍 <b>Введите название города:</b>\n\n"
        "<i>Например: Воронеж, Тюмень, Владивосток</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SearchStates.entering_city)
async def process_city_input(message: Message, state: FSMContext):
    city_name = message.text.strip()
    
    await message.answer("🔍 Ищу город...")
    
    # Поиск города через API
    cities = await hh.search_area(city_name)
    
    if not cities:
        await message.answer(
            f"😔 Город «{city_name}» не найден.\n\n"
            "Попробуйте другое название:",
            reply_markup=kb.back_kb("filter_city")
        )
        return
    
    if len(cities) == 1:
        # Один результат — сразу применяем
        city = cities[0]
        await state.update_data(
            city=city.get("id"),
            city_name=city.get("text", city.get("name"))
        )
        await state.set_state(None)
        
        data = await state.get_data()
        
        await message.answer(
            f"✅ Выбран город: <b>{city.get('text', city.get('name'))}</b>\n\n"
            f"🔍 Запрос: <b>{data.get('query')}</b>",
            reply_markup=kb.filters_kb(data),
            parse_mode="HTML"
        )
    else:
        # Несколько результатов — показываем выбор
        await state.set_state(None)
        await message.answer(
            f"📍 Найдено несколько городов по запросу «{city_name}»:\n\n"
            "Выберите нужный:",
            reply_markup=kb.found_cities_kb(cities)
        )


@router.callback_query(F.data.startswith("set_city_"))
async def set_city(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.replace("set_city_", "").split("_", 1)
    
    if parts[0] == "any":
        await state.update_data(city=None, city_name=None)
        city_display = "Любой"
    else:
        city_id = parts[0]
        city_name = parts[1] if len(parts) > 1 else "Город"
        await state.update_data(city=city_id, city_name=city_name)
        city_display = city_name
    
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"✅ Город: <b>{city_display}</b>\n\n"
        f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer(f"✅ Выбрано: {city_display}")


# ==================== ЗАРПЛАТА ====================

@router.callback_query(F.data == "filter_salary")
async def filter_salary(callback: CallbackQuery):
    await 
