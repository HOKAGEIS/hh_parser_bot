from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
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
    entering_salary = State()


# ==================== НАЧАЛО ПОИСКА ====================

@router.message(F.text == "🔍 Поиск вакансий")
async def start_search(message: Message, state: FSMContext):
    await state.clear()
    
    # Получаем популярные запросы пользователя
    popular = await db.get_popular_queries(message.from_user.id)
    
    text = "🔍 <b>Поиск вакансий</b>\n\n"
    text += "Введите название профессии или ключевые слова:\n\n"
    text += "<i>Примеры: Python разработчик, менеджер по продажам, дизайнер</i>"
    
    if popular:
        text += "\n\n📊 Ваши частые запросы:\n"
        for q in popular[:3]:
            text += f"• {q}\n"
    
    await state.set_state(SearchStates.entering_query)
    await message.answer(text, parse_mode="HTML")


@router.message(SearchStates.entering_query)
async def process_search_query(message: Message, state: FSMContext):
    query = message.text.strip()
    
    if len(query) < 2:
        await message.answer("⚠️ Запрос слишком короткий. Введите минимум 2 символа.")
        return
    
    # Получаем настройки пользователя
    user = await db.get_user(message.from_user.id)
    
    # Сохраняем запрос и фильтры
    await state.update_data(
        query=query,
        city=user.default_city if user else None,
        experience=user.default_experience if user else None,
        schedule=user.default_schedule if user else None,
        salary=user.min_salary if user else None,
        only_with_salary=user.only_with_salary if user else False,
        page=0
    )
    
    await message.answer(
        f"🔍 Запрос: <b>{query}</b>\n\n"
        "Выберите действие:",
        reply_markup=kb.search_options_kb(),
        parse_mode="HTML"
    )


# ==================== ФИЛЬТРЫ ====================

@router.callback_query(F.data == "search_filters")
async def show_filters(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    current_filters = {
        "city": data.get("city"),
        "experience": data.get("experience"),
        "schedule": data.get("schedule"),
        "salary": data.get("salary"),
    }
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{data.get('query')}</b>\n\n"
        "🎛 <b>Настройте фильтры:</b>",
        reply_markup=kb.filters_kb(current_filters),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "filter_city")
async def filter_city(callback: CallbackQuery):
    await callback.message.edit_text(
        "📍 <b>Выберите город:</b>",
        reply_markup=kb.cities_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_city_"))
async def set_city(callback: CallbackQuery, state: FSMContext):
    city = callback.data.replace("set_city_", "")
    if city == "any":
        city = None
    
    await state.update_data(city=city)
    
    # Возвращаемся к фильтрам
    data = await state.get_data()
    current_filters = {
        "city": data.get("city"),
        "experience": data.get("experience"),
        "schedule": data.get("schedule"),
        "salary": data.get("salary"),
    }
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{data.get('query')}</b>\n\n"
        "🎛 <b>Настройте фильтры:</b>",
        reply_markup=kb.filters_kb(current_filters),
        parse_mode="HTML"
    )
    await callback.answer("✅ Город выбран")


@router.callback_query(F.data == "filter_experience")
async def filter_experience(callback: CallbackQuery):
    await callback.message.edit_text(
        "💼 <b>Выберите требуемый опыт:</b>",
        reply_markup=kb.experience_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_exp_"))
async def set_experience(callback: CallbackQuery, state: FSMContext):
    exp = callback.data.replace("set_exp_", "")
    if exp == "any":
        exp = None
    
    await state.update_data(experience=exp)
    
    data = await state.get_data()
    current_filters = {
        "city": data.get("city"),
        "experience": data.get("experience"),
        "schedule": data.get("schedule"),
        "salary": data.get("salary"),
    }
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{data.get('query')}</b>\n\n"
        "🎛 <b>Настройте фильтры:</b>",
        reply_markup=kb.filters_kb(current_filters),
        parse_mode="HTML"
    )
    await callback.answer("✅ Опыт выбран")


@router.callback_query(F.data == "filter_schedule")
async def filter_schedule(callback: CallbackQuery):
    await callback.message.edit_text(
        "⏰ <b>Выберите график работы:</b>",
        reply_markup=kb.schedule_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_schedule_"))
async def set_schedule(callback: CallbackQuery, state: FSMContext):
    schedule = callback.data.replace("set_schedule_", "")
    if schedule == "any":
        schedule = None
    
    await state.update_data(schedule=schedule)
    
    data = await state.get_data()
    current_filters = {
        "city": data.get("city"),
        "experience": data.get("experience"),
        "schedule": data.get("schedule"),
        "salary": data.get("salary"),
    }
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{data.get('query')}</b>\n\n"
        "🎛 <b>Настройте фильтры:</b>",
        reply_markup=kb.filters_kb(current_filters),
        parse_mode="HTML"
    )
    await callback.answer("✅ График выбран")


@router.callback_query(F.data == "filter_salary")
async def filter_salary(callback: CallbackQuery):
    await callback.message.edit_text(
        "💰 <b>Выберите минимальную зарплату:</b>",
        reply_markup=kb.salary_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_salary_"))
async def set_salary(callback: CallbackQuery, state: FSMContext):
    salary = callback.data.replace("set_salary_", "")
    if salary == "any":
        salary = None
    else:
        salary = int(salary)
    
    await state.update_data(salary=salary)
    
    data = await state.get_data()
    current_filters = {
        "city": data.get("city"),
        "experience": data.get("experience"),
        "schedule": data.get("schedule"),
        "salary": data.get("salary"),
    }
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{data.get('query')}</b>\n\n"
        "🎛 <b>Настройте фильтры:</b>",
        reply_markup=kb.filters_kb(current_filters),
        parse_mode="HTML"
    )
    await callback.answer("✅ Зарплата выбрана")


@router.callback_query(F.data == "filter_reset")
async def reset_filters(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(
        city=None,
        experience=None,
        schedule=None,
        salary=None
    )
    
    current_filters = {}
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{data.get('query')}</b>\n\n"
        "🎛 <b>Настройте фильтры:</b>",
        reply_markup=kb.filters_kb(current_filters),
        parse_mode="HTML"
    )
    await callback.answer("🔄 Фильтры сброшены")


@router.callback_query(F.data == "back_to_filters")
async def back_to_filters(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_filters = {
        "city": data.get("city"),
        "experience": data.get("experience"),
        "schedule": data.get("schedule"),
        "salary": data.get("salary"),
    }
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{data.get('query')}</b>\n\n"
        "🎛 <b>Настройте фильтры:</b>",
        reply_markup=kb.filters_kb(current_filters),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== ВЫПОЛНЕНИЕ ПОИСКА ====================

@router.callback_query(F.data == "search_now")
async def execute_search(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    await callback.message.edit_text("🔄 Ищу вакансии...")
    
    # Выполняем поиск
    vacancies, total = await hh.search_vacancies(
        text=data.get("query"),
        area=data.get("city"),
        experience=data.get("experience"),
        schedule=data.get("schedule"),
        salary=data.get("salary"),
        only_with_salary=data.get("only_with_salary", False),
        page=0,
        per_page=config.VACANCIES_PER_PAGE
    )
    
    # Сохраняем в историю
    await db.add_search_history(
        callback.from_user.id,
        data.get("query"),
        total
    )
    
    if not vacancies:
        await callback.message.edit_text(
            "😔 По вашему запросу ничего не найдено.\n\n"
            "Попробуйте:\n"
            "• Изменить ключевые слова\n"
            "• Сбросить фильтры\n"
            "• Выбрать другой город",
            reply_markup=kb.search_options_kb()
        )
        return
    
    # Сохраняем результаты
    vacancies_data = [
        {
            "id": v.id,
            "name": v.name,
            "url": v.url,
            "employer": v.employer,
            "salary_from": v.salary_from,
            "salary_to": v.salary_to,
            "salary_currency": v.salary_currency,
            "city": v.city,
            "experience": v.experience,
            "schedule": v.schedule,
            "requirement": v.requirement,
        }
        for v in vacancies
    ]
    
    await state.update_data(
        vacancies=vacancies_data,
        total=total,
        page=0
    )
    await state.set_state(SearchStates.viewing_results)
    
    # Показываем первую вакансию
    await show_vacancy(callback.message, state, callback.from_user.id, 0, vacancies[0], total)
    await callback.answer()


async def show_vacancy(message, state: FSMContext, user_id: int, page: int, vacancy: Vacancy, total: int):
    """Показать вакансию"""
    is_fav = await db.is_favorite(user_id, vacancy.id)
    total_pages = (total + config.VACANCIES_PER_PAGE - 1) // config.VACANCIES_PER_PAGE
    
    await message.edit_text(
        vacancy.to_message(),
        reply_markup=kb.vacancy_kb(vacancy.id, is_fav, page, min(total_pages, 20)),
        parse_mode="HTML",
        disable_web_page_preview=True
    )


# ==================== НАВИГАЦИЯ ====================

@router.callback_query(F.data.startswith("page_"), SearchStates.viewing_results)
async def change_page(callback: CallbackQuery, state: FSMContext):
    if callback.data == "page_info":
        await callback.answer()
        return
    
    page = int(callback.data.replace("page_", ""))
    data = await state.get_data()
    
    await callback.message.edit_text("🔄 Загружаю...")
    
    # Загружаем новую страницу
    vacancies, total = await hh.search_vacancies(
        text=data.get("query"),
        area=data.get("city"),
        experience=data.get("experience"),
        schedule=data.get("schedule"),
        salary=data.get("salary"),
        only_with_salary=data.get("only_with_salary", False),
        page=page,
        per_page=config.VACANCIES_PER_PAGE
    )
    
    if not vacancies:
        await callback.message.edit_text("😔 Больше вакансий нет")
        await callback.answer()
        return
    
    # Обновляем данные
    vacancies_data = [
        {
            "id": v.id,
            "name": v.name,
            "url": v.url,
            "employer": v.employer,
            "salary_from": v.salary_from,
            "salary_to": v.salary_to,
            "salary_currency": v.salary_currency,
            "city": v.city,
            "experience": v.experience,
            "schedule": v.schedule,
            "requirement": v.requirement,
        }
        for v in vacancies
    ]
    
    await state.update_data(vacancies=vacancies_data, page=page)
    
    await show_vacancy(callback.message, state, callback.from_user.id, page, vacancies[0], total)
    await callback.answer()


# ==================== ИЗБРАННОЕ В ПОИСКЕ ====================

@router.callback_query(F.data.startswith("fav_"), SearchStates.viewing_results)
async def add_to_favorites(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.replace("fav_", "")
    data = await state.get_data()
    
    # Находим вакансию
    vacancy_data = None
    for v in data.get("vacancies", []):
        if v["id"] == vacancy_id:
            vacancy_data = v
            break
    
    if vacancy_data:
        success = await db.add_favorite(
            callback.from_user.id,
            vacancy_id,
            vacancy_data
        )
        
        if success:
            await callback.answer("⭐ Добавлено в избранное!")
        else:
            await callback.answer("Уже в избранном")
    else:
        await callback.answer("Ошибка")
    
    # Обновляем кнопки
    page = data.get("page", 0)
    total = data.get("total", 0)
    is_fav = await db.is_favorite(callback.from_user.id, vacancy_id)
    total_pages = (total + config.VACANCIES_PER_PAGE - 1) // config.VACANCIES_PER_PAGE
    
    await callback.message.edit_reply_markup(
        reply_markup=kb.vacancy_kb(vacancy_id, is_fav, page, min(total_pages, 20))
    )


@router.callback_query(F.data.startswith("unfav_"), SearchStates.viewing_results)
async def remove_from_favorites(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.replace("unfav_", "")
    
    await db.remove_favorite(callback.from_user.id, vacancy_id)
    await callback.answer("💔 Удалено из избранного")
    
    # Обновляем кнопки
    data = await state.get_data()
    page = data.get("page", 0)
    total = data.get("total", 0)
    total_pages = (total + config.VACANCIES_PER_PAGE - 1) // config.VACANCIES_PER_PAGE
    
    await callback.message.edit_reply_markup(
        reply_markup=kb.vacancy_kb(vacancy_id, False, page, min(total_pages, 20))
    )


# ==================== ПОДПИСКА ИЗ ПОИСКА ====================

@router.callback_query(F.data == "subscribe_current", SearchStates.viewing_results)
async def subscribe_current_search(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    # Проверяем лимит
    count = await db.get_subscriptions_count(callback.from_user.id)
    if count >= config.MAX_SUBSCRIPTIONS:
        await callback.answer(
            f"⚠️ Максимум {config.MAX_SUBSCRIPTIONS} подписок",
            show_alert=True
        )
        return
    
    # Создаём подписку
    sub_id = await db.add_subscription(
        user_id=callback.from_user.id,
        query=data.get("query"),
        city=data.get("city"),
        experience=data.get("experience"),
        schedule=data.get("schedule"),
        min_salary=data.get("salary")
    )
    
    await callback.answer(
        f"🔔 Подписка создана!\nВы будете получать уведомления о новых вакансиях.",
        show_alert=True
    )


# ==================== ЗАКРЫТЬ ====================

@router.callback_query(F.data == "close_search")
async def close_search(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отменено")
    await callback.answer()
