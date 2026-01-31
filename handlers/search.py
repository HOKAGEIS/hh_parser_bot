from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

import database as db
import keyboards as kb
from hh_api import hh, Vacancy
from config import config

router = Router()


class SearchStates(StatesGroup):
    entering_query = State()
    entering_city = State()
    entering_salary = State()
    entering_exclude_word = State()
    viewing_results = State()


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
        "• Дизайнер</i>",
        parse_mode="HTML"
    )


@router.message(SearchStates.entering_query)
async def process_search_query(message: Message, state: FSMContext):
    query = message.text.strip()
    
    # Игнорируем кнопки меню
    if query in config.MENU_BUTTONS:
        await state.clear()
        return
    
    if len(query) < 2:
        await message.answer("⚠️ Минимум 2 символа.")
        return
    
    # Получаем настройки пользователя
    user = await db.get_user(message.from_user.id)
    
    # Сохраняем в историю
    await db.add_search_history(message.from_user.id, query)
    
    await state.update_data(
        query=query,
        city=user.default_city if user else None,
        city_name=user.default_city_name if user else None,
        experience=user.default_experience if user else None,
        schedule=user.default_schedule if user else None,
        employment=None,
        salary=user.min_salary if user else None,
        only_with_salary=user.only_with_salary if user else False,
        exclude_words=user.exclude_words if user else [],
        search_period=0,
        search_field=None,
        education=None,
        with_address=False,
        accredited_it=False,
        exclude_agency=False,
        accept_handicapped=False,
        accept_kids=False,
        internship=False,
        page=0
    )
    
    data = await state.get_data()
    
    await message.answer(
        f"🔍 Запрос: <b>{query}</b>\n\n"
        "Настройте фильтры или начните поиск:",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML"
    )


# ==================== ИСТОРИЯ ПОИСКА ====================

@router.message(F.text == "🕐 История поиска")
async def show_search_history(message: Message):
    history = await db.get_search_history(message.from_user.id)
    
    if not history:
        await message.answer(
            "🕐 <b>История поиска</b>\n\n"
            "История пуста. Начните поиск вакансий!",
            reply_markup=kb.main_menu_kb(message.from_user.id),
            parse_mode="HTML"
        )
        return
    
    text = "🕐 <b>История поиска</b>\n\n"
    text += "Нажмите на запрос, чтобы повторить поиск:"
    
    await message.answer(
        text,
        reply_markup=kb.search_history_kb(history),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("repeat_search_"))
async def repeat_search(callback: CallbackQuery, state: FSMContext):
    index = int(callback.data.replace("repeat_search_", ""))
    
    history = await db.get_search_history(callback.from_user.id)
    
    if index >= len(history):
        await callback.answer("Запрос не найден")
        return
    
    item = history[index]
    query = item.get("query")
    
    user = await db.get_user(callback.from_user.id)
    
    await state.update_data(
        query=query,
        city=item.get("city") or (user.default_city if user else None),
        city_name=item.get("city_name") or (user.default_city_name if user else None),
        experience=user.default_experience if user else None,
        schedule=user.default_schedule if user else None,
        employment=None,
        salary=user.min_salary if user else None,
        only_with_salary=user.only_with_salary if user else False,
        exclude_words=user.exclude_words if user else [],
        search_period=0,
        page=0
    )
    
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{query}</b>\n\n"
        "Настройте фильтры или начните поиск:",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "clear_history")
async def clear_history(callback: CallbackQuery):
    await db.clear_search_history(callback.from_user.id)
    
    await callback.message.edit_text(
        "🕐 <b>История поиска</b>\n\n"
        "✅ История очищена.",
        parse_mode="HTML"
    )
    await callback.answer("История очищена")


# ==================== ФИЛЬТРЫ ====================

@router.callback_query(F.data == "back_to_filters")
async def back_to_filters(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    try:
        await callback.message.edit_text(
            f"🔍 Запрос: <b>{data.get('query')}</b>\n\n"
            "Настройте фильтры:",
            reply_markup=kb.filters_kb(data),
            parse_mode="HTML"
        )
    except:
        pass
    await callback.answer()


# ==================== ГОРОД ====================

@router.callback_query(F.data == "filter_city")
async def filter_city(callback: CallbackQuery):
    await callback.message.edit_text(
        "📍 <b>Выберите город</b>",
        reply_markup=kb.cities_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "detect_city")
async def detect_city(callback: CallbackQuery, state: FSMContext):
    await callback.answer("🔍 Определяю город...")
    
    city = await hh.detect_city_by_ip()
    
    if city:
        await state.update_data(city=city.get("id"), city_name=city.get("text"))
        data = await state.get_data()
        
        await callback.message.edit_text(
            f"✅ Определён город: <b>{city.get('text')}</b>\n\n"
            f"🔍 Запрос: <b>{data.get('query')}</b>",
            reply_markup=kb.filters_kb(data),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "😔 Не удалось определить город.\n"
            "Выберите вручную:",
            reply_markup=kb.cities_kb(),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "enter_city_manual")
async def enter_city_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.entering_city)
    
    await callback.message.edit_text(
        "📍 <b>Введите название города:</b>\n\n"
        "<i>Например: Воронеж, Тюмень</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SearchStates.entering_city)
async def process_city_input(message: Message, state: FSMContext):
    city_name = message.text.strip()
    
    if city_name in config.MENU_BUTTONS:
        await state.clear()
        return
    
    cities = await hh.search_area(city_name)
    
    if not cities:
        await message.answer(f"😔 Город «{city_name}» не найден. Попробуйте другой.")
        return
    
    if len(cities) == 1:
        city = cities[0]
        await state.update_data(city=city.get("id"), city_name=city.get("text", city.get("name")))
        await state.set_state(None)
        
        data = await state.get_data()
        
        await message.answer(
            f"✅ Выбран город: <b>{city.get('text', city.get('name'))}</b>\n\n"
            f"🔍 Запрос: <b>{data.get('query')}</b>",
            reply_markup=kb.filters_kb(data),
            parse_mode="HTML"
        )
    else:
        await state.set_state(None)
        
        builder = kb.InlineKeyboardBuilder()
        for city in cities[:8]:
            city_id = city.get("id")
            city_text = city.get("text", city.get("name", ""))
            builder.row(kb.InlineKeyboardButton(text=f"📍 {city_text}", callback_data=f"set_city_{city_id}_{city_text[:20]}"))
        builder.row(kb.InlineKeyboardButton(text="⬅️ Назад", callback_data="filter_city"))
        
        await message.answer(
            f"📍 Найдено несколько городов:",
            reply_markup=builder.as_markup()
        )


@router.callback_query(F.data.startswith("set_city_"))
async def set_city(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.replace("set_city_", "").split("_", 1)
    
    if parts[0] == "any":
        await state.update_data(city=None, city_name=None)
    else:
        city_id = parts[0]
        city_name = parts[1] if len(parts) > 1 else "Город"
        await state.update_data(city=city_id, city_name=city_name)
    
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== ЗАРПЛАТА ====================

@router.callback_query(F.data == "filter_salary")
async def filter_salary(callback: CallbackQuery):
    await callback.message.edit_text(
        "💰 <b>Минимальная зарплата</b>",
        reply_markup=kb.salary_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "enter_salary_manual")
async def enter_salary_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.entering_salary)
    
    await callback.message.edit_text(
        "💰 <b>Введите минимальную зарплату</b>\n\n"
        "<i>Только цифры, например: 80000</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SearchStates.entering_salary)
async def process_salary_input(message: Message, state: FSMContext):
    try:
        salary = int("".join(filter(str.isdigit, message.text)))
        
        if salary < 1000:
            await message.answer("⚠️ Слишком мало. Введите в рублях.")
            return
        
        await state.update_data(salary=salary)
        await state.set_state(None)
        
        data = await state.get_data()
        
        await message.answer(
            f"✅ Зарплата: от <b>{salary:,}₽</b>\n\n".replace(",", " ") +
            f"🔍 Запрос: <b>{data.get('query')}</b>",
            reply_markup=kb.filters_kb(data),
            parse_mode="HTML"
        )
    except:
        await message.answer("⚠️ Введите число")


@router.callback_query(F.data.startswith("set_salary_"))
async def set_salary(callback: CallbackQuery, state: FSMContext):
    salary_str = callback.data.replace("set_salary_", "")
    salary = None if salary_str == "any" else int(salary_str)
    
    await state.update_data(salary=salary)
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== ОПЫТ ====================

@router.callback_query(F.data == "filter_experience")
async def filter_experience(callback: CallbackQuery):
    await callback.message.edit_text(
        "💼 <b>Требуемый опыт работы</b>",
        reply_markup=kb.experience_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_exp_"))
async def set_experience(callback: CallbackQuery, state: FSMContext):
    exp = callback.data.replace("set_exp_", "")
    exp = None if exp == "any" else exp
    
    await state.update_data(experience=exp)
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== ГРАФИК ====================

@router.callback_query(F.data == "filter_schedule")
async def filter_schedule(callback: CallbackQuery):
    await callback.message.edit_text(
        "⏰ <b>График работы</b>",
        reply_markup=kb.schedule_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_schedule_"))
async def set_schedule(callback: CallbackQuery, state: FSMContext):
    schedule = callback.data.replace("set_schedule_", "")
    schedule = None if schedule == "any" else schedule
    
    await state.update_data(schedule=schedule)
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== ЗАНЯТОСТЬ ====================

@router.callback_query(F.data == "filter_employment")
async def filter_employment(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 <b>Тип занятости</b>",
        reply_markup=kb.employment_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_employment_"))
async def set_employment(callback: CallbackQuery, state: FSMContext):
    emp = callback.data.replace("set_employment_", "")
    emp = None if emp == "any" else emp
    
    await state.update_data(employment=emp)
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== ПЕРИОД ====================

@router.callback_query(F.data == "filter_period")
async def filter_period(callback: CallbackQuery):
    await callback.message.edit_text(
        "📅 <b>Период публикации</b>",
        reply_markup=kb.period_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_period_"))
async def set_period(callback: CallbackQuery, state: FSMContext):
    period = int(callback.data.replace("set_period_", ""))
    
    await state.update_data(search_period=period)
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== РАСШИРЕННЫЕ ФИЛЬТРЫ ====================

@router.callback_query(F.data == "filter_advanced")
async def filter_advanced(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    await callback.message.edit_text(
        "🔧 <b>Расширенные фильтры</b>",
        reply_markup=kb.advanced_filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "filter_search_field")
async def filter_search_field(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔎 <b>Искать в:</b>",
        reply_markup=kb.search_field_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_search_field_"))
async def set_search_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.replace("set_search_field_", "")
    field = None if field == "any" else field
    
    await state.update_data(search_field=field)
    data = await state.get_data()
    
    await callback.message.edit_text(
        "🔧 <b>Расширенные фильтры</b>",
        reply_markup=kb.advanced_filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "filter_education")
async def filter_education(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎓 <b>Образование:</b>",
        reply_markup=kb.education_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_education_"))
async def set_education(callback: CallbackQuery, state: FSMContext):
    edu = callback.data.replace("set_education_", "")
    edu = None if edu == "any" else edu
    
    await state.update_data(education=edu)
    data = await state.get_data()
    
    await callback.message.edit_text(
        "🔧 <b>Расширенные фильтры</b>",
        reply_markup=kb.advanced_filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== TOGGLE ФИЛЬТРЫ ====================

@router.callback_query(F.data == "toggle_with_address")
async def toggle_with_address(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(with_address=not data.get("with_address", False))
    data = await state.get_data()
    
    await callback.message.edit_reply_markup(reply_markup=kb.advanced_filters_kb(data))
    await callback.answer()


@router.callback_query(F.data == "toggle_accredited_it")
async def toggle_accredited_it(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(accredited_it=not data.get("accredited_it", False))
    data = await state.get_data()
    
    await callback.message.edit_reply_markup(reply_markup=kb.advanced_filters_kb(data))
    await callback.answer()


@router.callback_query(F.data == "toggle_no_agency")
async def toggle_no_agency(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(exclude_agency=not data.get("exclude_agency", False))
    data = await state.get_data()
    
    await callback.message.edit_reply_markup(reply_markup=kb.advanced_filters_kb(data))
    await callback.answer()


@router.callback_query(F.data == "toggle_handicapped")
async def toggle_handicapped(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(accept_handicapped=not data.get("accept_handicapped", False))
    data = await state.get_data()
    
    await callback.message.edit_reply_markup(reply_markup=kb.advanced_filters_kb(data))
    await callback.answer()


@router.callback_query(F.data == "toggle_accept_kids")
async def toggle_accept_kids(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(accept_kids=not data.get("accept_kids", False))
    data = await state.get_data()
    
    await callback.message.edit_reply_markup(reply_markup=kb.advanced_filters_kb(data))
    await callback.answer()


@router.callback_query(F.data == "toggle_internship")
async def toggle_internship(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_val = not data.get("internship", False)
    await state.update_data(internship=new_val)
    
    # Если стажировка — ставим employment=probation
    if new_val:
        await state.update_data(employment="probation")
    
    data = await state.get_data()
    await callback.message.edit_reply_markup(reply_markup=kb.advanced_filters_kb(data))
    await callback.answer()


# ==================== ИСКЛЮЧЕНИЯ ====================

@router.callback_query(F.data == "filter_exclude")
async def filter_exclude(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    words = data.get("exclude_words", [])
    
    await callback.message.edit_text(
        "🚫 <b>Слова-исключения</b>\n\n" +
        (", ".join(words) if words else "Список пуст"),
        reply_markup=kb.exclude_words_kb(words),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "add_exclude_word")
async def add_exclude_word(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.entering_exclude_word)
    
    await callback.message.edit_text(
        "🚫 <b>Введите слово для исключения:</b>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SearchStates.entering_exclude_word)
async def process_exclude_word(message: Message, state: FSMContext):
    word = message.text.strip().lower()
    
    if word in config.MENU_BUTTONS:
        await state.clear()
        return
    
    if len(word) < 2:
        await message.answer("⚠️ Слишком короткое")
        return
    
    data = await state.get_data()
    words = data.get("exclude_words", [])
    
    if word not in words:
        words.append(word)
        await state.update_data(exclude_words=words)
    
    await state.set_state(None)
    
    await message.answer(
        f"✅ Добавлено: <b>{word}</b>",
        reply_markup=kb.exclude_words_kb(words),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("remove_exclude_"))
async def remove_exclude(callback: CallbackQuery, state: FSMContext):
    word = callback.data.replace("remove_exclude_", "")
    
    data = await state.get_data()
    words = data.get("exclude_words", [])
    
    if word in words:
        words.remove(word)
        await state.update_data(exclude_words=words)
    
    await callback.message.edit_text(
        "🚫 <b>Слова-исключения</b>\n\n" +
        (", ".join(words) if words else "Список пуст"),
        reply_markup=kb.exclude_words_kb(words),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "clear_exclude_words")
async def clear_exclude_words(callback: CallbackQuery, state: FSMContext):
    await state.update_data(exclude_words=[])
    
    await callback.message.edit_text(
        "🚫 <b>Слова-исключения</b>\n\n✅ Очищено",
        reply_markup=kb.exclude_words_kb([]),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== СБРОС ====================

@router.callback_query(F.data == "filter_reset")
async def filter_reset(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    query = data.get("query")
    
    await state.update_data(
        city=None, city_name=None, experience=None, schedule=None,
        employment=None, salary=None, only_with_salary=False,
        exclude_words=[], search_period=0, search_field=None,
        education=None, with_address=False, accredited_it=False,
        exclude_agency=False, accept_handicapped=False,
        accept_kids=False, internship=False
    )
    
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"🔄 Фильтры сброшены\n\n🔍 Запрос: <b>{query}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== ПОИСК ====================

@router.callback_query(F.data == "search_now")
async def execute_search(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    await callback.message.edit_text("🔍 Ищу вакансии...")
    
    vacancies, total = await hh.search_vacancies(
        text=data.get("query"),
        area=data.get("city"),
        experience=data.get("experience"),
        schedule=data.get("schedule"),
        employment=data.get("employment"),
        salary=data.get("salary"),
        only_with_salary=data.get("only_with_salary", False),
        exclude_words=data.get("exclude_words", []),
        page=0,
        per_page=config.VACANCIES_PER_PAGE,
        search_period=data.get("search_period"),
        search_field=data.get("search_field"),
        education=data.get("education"),
        accept_kids=data.get("accept_kids", False),
        accept_handicapped=data.get("accept_handicapped", False),
        accredited_it_employer=data.get("accredited_it", False),
        with_address=data.get("with_address", False),
        exclude_agency=data.get("exclude_agency", False),
    )
    
    if not vacancies:
        await callback.message.edit_text(
            "😔 Ничего не найдено.\n\n"
            "Попробуйте изменить фильтры.",
            reply_markup=kb.filters_kb(data)
        )
        return
    
    # Сохраняем
    vacancies_data = [{
        "id": v.id, "name": v.name, "url": v.url, "employer": v.employer,
        "salary_from": v.salary_from, "salary_to": v.salary_to,
        "salary_currency": v.salary_currency, "city": v.city,
        "experience": v.experience, "schedule": v.schedule,
        "employment": v.employment, "requirement": v.requirement,
        "address": v.address, "employer_accredited": v.employer_accredited,
    } for v in vacancies]
    
    await state.update_data(vacancies=vacancies_data, total=total, page=0)
    await state.set_state(SearchStates.viewing_results)
    
    await show_vacancy(callback.message, vacancies[0], 0, total, callback.from_user.id)
    await callback.answer()


async def show_vacancy(message, vacancy: Vacancy, page: int, total: int, user_id: int):
    is_fav = await db.is_favorite(user_id, vacancy.id)
    total_pages = (total + config.VACANCIES_PER_PAGE - 1) // config.VACANCIES_PER_PAGE
    
    text = f"📊 <b>Найдено: {total:,} вакансий</b>\n\n".replace(",", " ")
    text += vacancy.to_short_message()
    
    await message.edit_text(
        text,
        reply_markup=kb.vacancy_kb(vacancy.id, is_fav, page, total_pages),
        parse_mode="HTML",
        disable_web_page_preview=True
    )


# ==================== НАВИГАЦИЯ ====================

@router.callback_query(F.data.startswith("page_"), SearchStates.viewing_results)
async def change_page(callback: CallbackQuery, state: FSMContext):
    if callback.data == "page_info":
        data = await state.get_data()
        await callback.answer(f"Всего: {data.get('total', 0)} вакансий", show_alert=True)
        return
    
    page = int(callback.data.replace("page_", ""))
    data = await state.get_data()
    
    await callback.message.edit_text("🔄 Загружаю...")
    
    vacancies, total = await hh.search_vacancies(
        text=data.get("query"),
        area=data.get("city"),
        experience=data.get("experience"),
        schedule=data.get("schedule"),
        employment=data.get("employment"),
        salary=data.get("salary"),
        only_with_salary=data.get("only_with_salary", False),
        exclude_words=data.get("exclude_words", []),
        page=page,
        per_page=config.VACANCIES_PER_PAGE,
        search_period=data.get("search_period"),
        search_field=data.get("search_field"),
        education=data.get("education"),
        accept_kids=data.get("accept_kids", False),
        accept_handicapped=data.get("accept_handicapped", False),
        accredited_it_employer=data.get("accredited_it", False),
        with_address=data.get("with_address", False),
        exclude_agency=data.get("exclude_agency", False),
    )
    
    if not vacancies:
        await callback.message.edit_text("😔 Больше нет")
        return
    
    await state.update_data(page=page, total=total)
    await show_vacancy(callback.message, vacancies[0], page, total, callback.from_user.id)
    await callback.answer()


# ==================== ИЗБРАННОЕ ====================

@router.callback_query(F.data.startswith("fav_"))
async def add_to_fav(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.replace("fav_", "")
    data = await state.get_data()
    
    for v in data.get("vacancies", []):
        if v["id"] == vacancy_id:
            await db.add_favorite(callback.from_user.id, vacancy_id, v)
            break
    
    await callback.answer("⭐ Добавлено в избранное!")


@router.callback_query(F.data.startswith("unfav_"))
async def remove_from_fav(callback: CallbackQuery):
    vacancy_id = callback.data.replace("unfav_", "")
    await db.remove_favorite(callback.from_user.id, vacancy_id)
    await callback.answer("💔 Удалено из избранного")


# ==================== ПОДРОБНЕЕ ====================

@router.callback_query(F.data.startswith("full_"))
async def show_full_vacancy(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.replace("full_", "")
    
    await callback.message.edit_text("📄 Загружаю...")
    
    vacancy = await hh.get_vacancy_full(vacancy_id)
    
    if not vacancy:
        await callback.answer("❌ Не удалось загрузить")
        return
    
    text = vacancy.to_short_message()
    
    if vacancy.description:
        import re
        desc = re.sub(r'<[^>]+>', '', vacancy.description)[:2000]
        text += f"\n\n📝 <b>Описание:</b>\n{desc}"
    
    if vacancy.key_skills:
        text += f"\n\n🛠 <b>Навыки:</b>\n{', '.join(vacancy.key_skills[:10])}"
    
    if len(text) > 4000:
        text = text[:4000] + "..."
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.vacancy_full_kb(vacancy_id),
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_list")
async def back_to_list(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    vacancies = data.get("vacancies", [])
    page = data.get("page", 0)
    total = data.get("total", 0)
    
    if not vacancies:
        await callback.message.edit_text("Нет результатов")
        return
    
    v = vacancies[0]
    vacancy = Vacancy(
        id=v["id"], name=v["name"], url=v["url"], employer=v["employer"],
        employer_id=None, employer_logo=None,
        salary_from=v.get("salary_from"), salary_to=v.get("salary_to"),
        salary_currency=v.get("salary_currency"), city=v.get("city", ""),
        experience=v.get("experience", ""), schedule=v.get("schedule", ""),
        employment=v.get("employment", ""), requirement=v.get("requirement"),
        responsibility=None, description=None, key_skills=[],
        published_at="", has_test=False, response_letter_required=False,
        address=v.get("address"), employer_accredited=v.get("employer_accredited", False)
    )
    
    await show_vacancy(callback.message, vacancy, page, total, callback.from_user.id)
    await callback.answer()


# ==================== ПОДПИСКА ====================

@router.callback_query(F.data == "subscribe_current")
async def subscribe_current(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    query = data.get("query")
    
    if not query:
        await callback.answer("❌ Нет активного поиска")
        return
    
    count = await db.get_subscriptions_count(callback.from_user.id)
    if count >= config.MAX_SUBSCRIPTIONS:
        await callback.answer(f"⚠️ Максимум {config.MAX_SUBSCRIPTIONS} подписок", show_alert=True)
        return
    
    await db.add_subscription(
        user_id=callback.from_user.id,
        query=query,
        city=data.get("city"),
        city_name=data.get("city_name"),
        experience=data.get("experience"),
        schedule=data.get("schedule"),
        min_salary=data.get("salary"),
        exclude_words=data.get("exclude_words", [])
    )
    
    await callback.answer("🔔 Подписка создана!", show_alert=True)


# ==================== ЗАКРЫТЬ ====================

@router.callback_query(F.data == "close_search")
async def close_search(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🔍 Поиск завершён.")
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отменено")
    await callback.answer()
from aiogram.types import Message, CallbackQuery, ContentType

# ==================== ГЕОЛОКАЦИЯ ====================

@router.callback_query(F.data == "request_location")
async def request_location(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.entering_city)
    
    await callback.message.answer(
        "📍 <b>Определение города</b>\n\n"
        "Нажмите кнопку ниже, чтобы отправить ваше местоположение.\n\n"
        "<i>Или напишите название города вручную.</i>",
        reply_markup=kb.location_request_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== ГЕОЛОКАЦИЯ ====================

@router.callback_query(F.data == "detect_city")
async def detect_city(callback: CallbackQuery, state: FSMContext):
    """Попытка автоопределения города по IP (может не работать на сервере)"""
    await callback.answer("🔍 Определяю...")
    
    city = await hh.detect_city_by_ip()
    
    data = await state.get_data()
    
    if city:
        await state.update_data(city=city.get("id"), city_name=city.get("text"))
        data = await state.get_data()
        
        try:
            await callback.message.edit_text(
                f"✅ Город: <b>{city.get('text')}</b>\n\n"
                f"🔍 Запрос: <b>{data.get('query')}</b>",
                reply_markup=kb.filters_kb(data),
                parse_mode="HTML"
            )
        except:
            await callback.message.answer(
                f"✅ Город: <b>{city.get('text')}</b>",
                reply_markup=kb.filters_kb(data),
                parse_mode="HTML"
            )
    else:
        try:
            await callback.message.edit_text(
                "😔 Не удалось определить автоматически.\n\n"
                "📍 Отправьте геолокацию или выберите город:",
                reply_markup=kb.cities_kb(),
                parse_mode="HTML"
            )
        except:
            pass


@router.callback_query(F.data == "request_location")
async def request_location(callback: CallbackQuery, state: FSMContext):
    """Запрос геолокации у пользователя"""
    await state.set_state(SearchStates.entering_city)
    await state.update_data(waiting_location=True)
    
    await callback.message.answer(
        "📍 <b>Отправьте геолокацию</b>\n\n"
        "Нажмите кнопку ниже или напишите название города:",
        reply_markup=kb.location_request_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(F.location)
async def process_location(message: Message, state: FSMContext):
    """Обработка полученной геолокации"""
    lat = message.location.latitude
    lon = message.location.longitude
    
    await message.answer(
        "🔍 Определяю город...",
        reply_markup=kb.main_menu_kb(message.from_user.id)
    )
    
    city = await find_city_by_coordinates(lat, lon)
    
    if city:
        await state.update_data(
            city=city.get("id"),
            city_name=city.get("name"),
            waiting_location=False
        )
        await state.set_state(None)
        
        data = await state.get_data()
        query = data.get("query")
        
        if query:
            await message.answer(
                f"✅ Город: <b>{city.get('name')}</b>\n\n"
                f"🔍 Запрос: <b>{query}</b>",
                reply_markup=kb.filters_kb(data),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"✅ Город установлен: <b>{city.get('name')}</b>\n\n"
                "Теперь начните поиск!",
                reply_markup=kb.main_menu_kb(message.from_user.id),
                parse_mode="HTML"
            )
    else:
        await state.set_state(None)
        await message.answer(
            "😔 Не удалось определить город.\n"
            "Введите название вручную через поиск.",
            reply_markup=kb.main_menu_kb(message.from_user.id)
        )


async def find_city_by_coordinates(lat: float, lon: float) -> dict:
    """Найти город по координатам"""
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&accept-language=ru"
            headers = {"User-Agent": "HH-Parser-Bot/1.0"}
            
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    address = data.get("address", {})
                    
                    city_name = (
                        address.get("city") or
                        address.get("town") or
                        address.get("village") or
                        address.get("state") or
                        address.get("county")
                    )
                    
                    if city_name:
                        cities = await hh.search_area(city_name)
                        if cities:
                            return {
                                "id": cities[0].get("id"),
                                "name": cities[0].get("text", city_name)
                            }
    except Exception as e:
        print(f"Ошибка геолокации: {e}")
    
    return None


@router.message(F.text == "❌ Отмена")
async def cancel_location_request(message: Message, state: FSMContext):
    """Отмена запроса геолокации"""
    data = await state.get_data()
    query = data.get("query")
    
    await state.update_data(waiting_location=False)
    await state.set_state(None)
    
    if query:
        await message.answer(
            f"🔍 Запрос: <b>{query}</b>\n\n"
            "Выберите город из списка:",
            reply_markup=kb.main_menu_kb(message.from_user.id),
            parse_mode="HTML"
        )
        # Отправляем инлайн клавиатуру с городами
        await message.answer(
            "📍 Выберите город:",
            reply_markup=kb.cities_kb()
        )
    else:
        await message.answer(
            "❌ Отменено",
            reply_markup=kb.main_menu_kb(message.from_user.id)
        )
