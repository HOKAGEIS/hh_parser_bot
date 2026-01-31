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
    
    # Игнорируем кнопки меню
    if query in config.MENU_BUTTONS:
        await state.clear()
        return
    
    if len(query) < 2:
        await message.answer("⚠️ Запрос слишком короткий. Минимум 2 символа.")
        return
    
    # ДОБАВЬ ЭТУ СТРОКУ:
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
    await callback.message.edit_text(
        "💰 <b>Минимальная зарплата</b>\n\n"
        "Выберите или введите свою сумму:",
        reply_markup=kb.salary_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "enter_salary_manual")
async def enter_salary_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.entering_salary)
    
    await callback.message.edit_text(
        "💰 <b>Введите минимальную зарплату</b>\n\n"
        "Введите число (только цифры):\n\n"
        "<i>Например: 80000, 150000, 250000</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SearchStates.entering_salary)
async def process_salary_input(message: Message, state: FSMContext):
    try:
        # Убираем пробелы и всё кроме цифр
        salary_text = "".join(filter(str.isdigit, message.text))
        salary = int(salary_text)
        
        if salary < 1000:
            await message.answer("⚠️ Слишком маленькая сумма. Введите в рублях (например: 50000)")
            return
        
        if salary > 10000000:
            await message.answer("⚠️ Слишком большая сумма. Максимум 10 000 000")
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
    except ValueError:
        await message.answer("⚠️ Введите число. Например: 100000")


@router.callback_query(F.data.startswith("set_salary_"))
async def set_salary(callback: CallbackQuery, state: FSMContext):
    salary_str = callback.data.replace("set_salary_", "")
    
    if salary_str == "any":
        salary = None
        salary_display = "Любая"
    else:
        salary = int(salary_str)
        salary_display = f"от {salary:,}₽".replace(",", " ")
    
    await state.update_data(salary=salary)
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"✅ Зарплата: <b>{salary_display}</b>\n\n"
        f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer(f"✅ {salary_display}")


# ==================== ИСКЛЮЧЕНИЯ ====================

@router.callback_query(F.data == "filter_exclude")
async def filter_exclude(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    words = data.get("exclude_words", [])
    
    text = "🚫 <b>Слова-исключения</b>\n\n"
    if words:
        text += "Вакансии с этими словами не будут показаны:\n"
        text += ", ".join([f"<code>{w}</code>" for w in words])
        text += "\n\nНажмите на слово чтобы удалить."
    else:
        text += "Список пуст. Добавьте слова, которые хотите исключить из поиска.\n\n"
        text += "<i>Например: стажёр, junior, менеджер</i>"
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.exclude_words_kb(words),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "add_exclude_word")
async def add_exclude_word(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.entering_exclude_word)
    
    await callback.message.edit_text(
        "🚫 <b>Добавить слово-исключение</b>\n\n"
        "Введите слово или фразу для исключения:\n\n"
        "<i>Например: стажёр, без опыта, junior</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SearchStates.entering_exclude_word)
async def process_exclude_word(message: Message, state: FSMContext):
    word = message.text.strip().lower()
    
    if len(word) < 2:
        await message.answer("⚠️ Слишком короткое слово")
        return
    
    if len(word) > 50:
        await message.answer("⚠️ Слишком длинное слово (макс. 50 символов)")
        return
    
    data = await state.get_data()
    words = data.get("exclude_words", [])
    
    if len(words) >= config.MAX_EXCLUDE_WORDS:
        await message.answer(f"⚠️ Максимум {config.MAX_EXCLUDE_WORDS} слов")
        return
    
    if word not in words:
        words.append(word)
        await state.update_data(exclude_words=words)
    
    await state.set_state(None)
    
    await message.answer(
        f"✅ Добавлено: <b>{word}</b>\n\n"
        f"Исключений: {len(words)}",
        reply_markup=kb.exclude_words_kb(words),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("remove_exclude_"))
async def remove_exclude_word(callback: CallbackQuery, state: FSMContext):
    word = callback.data.replace("remove_exclude_", "")
    
    data = await state.get_data()
    words = data.get("exclude_words", [])
    
    if word in words:
        words.remove(word)
        await state.update_data(exclude_words=words)
    
    await callback.message.edit_text(
        "🚫 <b>Слова-исключения</b>\n\n" +
        (f"Список: {', '.join(words)}" if words else "Список пуст"),
        reply_markup=kb.exclude_words_kb(words),
        parse_mode="HTML"
    )
    await callback.answer(f"✅ Удалено: {word}")


@router.callback_query(F.data == "clear_exclude_words")
async def clear_exclude_words(callback: CallbackQuery, state: FSMContext):
    await state.update_data(exclude_words=[])
    
    await callback.message.edit_text(
        "🚫 <b>Слова-исключения</b>\n\n"
        "Список очищен.",
        reply_markup=kb.exclude_words_kb([]),
        parse_mode="HTML"
    )
    await callback.answer("🗑 Список очищен")


# ==================== ОПЫТ И ГРАФИК ====================

@router.callback_query(F.data == "filter_experience")
async def filter_experience(callback: CallbackQuery):
    await callback.message.edit_text(
        "💼 <b>Требуемый опыт работы:</b>",
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
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer("✅ Опыт выбран")


@router.callback_query(F.data == "filter_schedule")
async def filter_schedule(callback: CallbackQuery):
    await callback.message.edit_text(
        "⏰ <b>График работы:</b>",
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
    
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer("✅ График выбран")


@router.callback_query(F.data == "filter_reset")
async def reset_filters(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(
        city=None,
        city_name=None,
        experience=None,
        schedule=None,
        salary=None,
        exclude_words=[]
    )
    
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"🔄 Фильтры сброшены\n\n"
        f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML"
    )
    await callback.answer("🔄 Сброшено")


# ==================== ПОИСК ====================

# В начале файла измени VACANCIES_PER_PAGE
# Или в config.py установи VACANCIES_PER_PAGE = 20

@router.callback_query(F.data == "search_now")
async def execute_search(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    await callback.message.edit_text("🔍 Ищу вакансии...")
    
    # Увеличиваем количество на странице
    per_page = 20  # Было 5
    
    vacancies, total = await hh.search_vacancies(
        text=data.get("query"),
        area=data.get("city"),
        experience=data.get("experience"),
        schedule=data.get("schedule"),
        salary=data.get("salary"),
        only_with_salary=data.get("only_with_salary", False),
        exclude_words=data.get("exclude_words", []),
        page=0,
        per_page=per_page
    )
    
    if not vacancies:
        await callback.message.edit_text(
            "😔 Ничего не найдено.\n\n"
            "Попробуйте:\n"
            "• Изменить запрос\n"
            "• Сбросить фильтры\n"
            "• Убрать слова-исключения",
            reply_markup=kb.filters_kb(data)
        )
        return
    
    # Сохраняем данные
    vacancies_data = []
    for v in vacancies:
        vacancies_data.append({
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
        })
    
    await state.update_data(
        vacancies=vacancies_data,
        total=total,
        page=0,
        current_index=0,  # Добавляем индекс текущей вакансии
        per_page=per_page
    )
    await state.set_state(SearchStates.viewing_results)
    
    # Показываем первую вакансию
    await show_vacancy_by_index(callback.message, vacancies_data, 0, total, callback.from_user.id, state)
    await callback.answer()


async def show_vacancy_by_index(message, vacancies: list, index: int, total: int, user_id: int, state: FSMContext):
    """Показ вакансии по индексу в текущем списке"""
    if index < 0 or index >= len(vacancies):
        return
    
    v = vacancies[index]
    is_fav = await db.is_favorite(user_id, v["id"])
    
    # Формируем зарплату
    salary_text = "💰 Зарплата не указана"
    if v.get("salary_from") or v.get("salary_to"):
        currency = {"RUR": "₽", "USD": "$", "EUR": "€"}.get(v.get("salary_currency"), "")
        if v.get("salary_from") and v.get("salary_to"):
            salary_text = f"💰 {v['salary_from']:,} - {v['salary_to']:,} {currency}".replace(",", " ")
        elif v.get("salary_from"):
            salary_text = f"💰 от {v['salary_from']:,} {currency}".replace(",", " ")
        else:
            salary_text = f"💰 до {v['salary_to']:,} {currency}".replace(",", " ")
    
    req = v.get("requirement") or ""
    # Очищаем HTML теги
    import re
    req = re.sub(r'<[^>]+>', '', req)
    if len(req) > 150:
        req = req[:150] + "..."
    
    text = (
        f"📊 <b>Найдено: {total:,} вакансий</b>\n"
        f"📄 Вакансия {index + 1} из {len(vacancies)} (загружено)\n\n"
        f"📌 <b>{v['name']}</b>\n\n"
        f"🏢 {v['employer']}\n"
        f"📍 {v['city']}\n"
        f"{salary_text}\n"
        f"📋 Опыт: {v['experience']}\n"
        f"⏰ {v['schedule']}\n\n"
        f"📝 {req}\n\n"
        f"🔗 <a href='{v['url']}'>Открыть на hh.ru</a>"
    ).replace(",", " ")
    
    data = await state.get_data()
    total_loaded = len(vacancies)
    can_load_more = total > total_loaded
    
    await message.edit_text(
        text,
        reply_markup=kb.vacancy_nav_kb(
            vacancy_id=v["id"],
            is_fav=is_fav,
            current_index=index,
            total_loaded=total_loaded,
            total_found=total,
            can_load_more=can_load_more
        ),
        parse_mode="HTML",
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "vacancy_prev", SearchStates.viewing_results)
async def vacancy_prev(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    vacancies = data.get("vacancies", [])
    current = data.get("current_index", 0)
    total = data.get("total", 0)
    
    if current > 0:
        current -= 1
        await state.update_data(current_index=current)
        await show_vacancy_by_index(callback.message, vacancies, current, total, callback.from_user.id, state)
    
    await callback.answer()


@router.callback_query(F.data == "vacancy_next", SearchStates.viewing_results)
async def vacancy_next(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    vacancies = data.get("vacancies", [])
    current = data.get("current_index", 0)
    total = data.get("total", 0)
    
    if current < len(vacancies) - 1:
        current += 1
        await state.update_data(current_index=current)
        await show_vacancy_by_index(callback.message, vacancies, current, total, callback.from_user.id, state)
    
    await callback.answer()


@router.callback_query(F.data == "load_more_vacancies", SearchStates.viewing_results)
async def load_more_vacancies(callback: CallbackQuery, state: FSMContext):
    """Загрузить ещё вакансии"""
    data = await state.get_data()
    vacancies = data.get("vacancies", [])
    total = data.get("total", 0)
    per_page = data.get("per_page", 20)
    
    # Вычисляем следующую страницу
    current_page = len(vacancies) // per_page
    
    if len(vacancies) >= total:
        await callback.answer("Все вакансии загружены")
        return
    
    await callback.answer("🔄 Загружаю ещё...")
    
    new_vacancies, _ = await hh.search_vacancies(
        text=data.get("query"),
        area=data.get("city"),
        experience=data.get("experience"),
        schedule=data.get("schedule"),
        salary=data.get("salary"),
        only_with_salary=data.get("only_with_salary", False),
        exclude_words=data.get("exclude_words", []),
        page=current_page,
        per_page=per_page
    )
    
    if new_vacancies:
        for v in new_vacancies:
            vacancies.append({
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
            })
        
        await state.update_data(vacancies=vacancies)
        
        # Показываем следующую вакансию
        current = data.get("current_index", 0) + 1
        await state.update_data(current_index=current)
        await show_vacancy_by_index(callback.message, vacancies, current, total, callback.from_user.id, state)
    else:
        await callback.answer("Больше вакансий нет")


# ==================== ПОЛНОЕ ОПИСАНИЕ ====================

@router.callback_query(F.data.startswith("full_"))
async def show_full_vacancy(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.replace("full_", "")
    
    await callback.message.edit_text("📄 Загружаю полное описание...")
    
    vacancy = await hh.get_vacancy_full(vacancy_id)
    
    if not vacancy:
        await callback.answer("❌ Не удалось загрузить вакансию", show_alert=True)
        return
    
    user = await db.get_user(callback.from_user.id)
    is_authorized = bool(user and user.hh_access_token)
    is_applied = await db.was_applied(callback.from_user.id, vacancy_id)
    
    # Разбиваем длинное сообщение
    text = vacancy.to_full_message()
    
    if len(text) > 4000:
        text = text[:4000] + "\n\n<i>...текст обрезан. Откройте на hh.ru для полной версии</i>"
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.vacancy_full_kb(vacancy_id, is_authorized, is_applied),
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
        await callback.message.edit_text("Нет результатов поиска")
        return
    
    # Воссоздаём объект вакансии
    v = vacancies[0]
    vacancy = Vacancy(
        id=v["id"], name=v["name"], url=v["url"], employer=v["employer"],
        employer_id=None, employer_logo=None,
        salary_from=v.get("salary_from"), salary_to=v.get("salary_to"),
        salary_currency=v.get("salary_currency"), city=v.get("city", ""),
        experience=v.get("experience", ""), schedule=v.get("schedule", ""),
        employment="", requirement=v.get("requirement"), responsibility=None,
        description=None, key_skills=[], published_at="",
        has_test=False, response_letter_required=False
    )
    
    user = await db.get_user(callback.from_user.id)
    is_authorized = bool(user and user.hh_access_token)
    
    await show_vacancy_message(callback.message, vacancy, page, total, callback.from_user.id, is_authorized)
    await callback.answer()


# ==================== ИЗБРАННОЕ ====================

@router.callback_query(F.data.startswith("fav_"))
async def add_to_fav(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.replace("fav_", "")
    data = await state.get_data()
    
    vacancy_data = None
    for v in data.get("vacancies", []):
        if v["id"] == vacancy_id:
            vacancy_data = v
            break
    
    if vacancy_data:
        await db.add_favorite(callback.from_user.id, vacancy_id, vacancy_data)
        await callback.answer("⭐ Добавлено в избранное!")
    else:
        await callback.answer("Ошибка")


@router.callback_query(F.data.startswith("unfav_"))
async def remove_from_fav(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.replace("unfav_", "")
    await db.remove_favorite(callback.from_user.id, vacancy_id)
    await callback.answer("💔 Удалено из избранного")


# ==================== ЗАКРЫТЬ ====================

@router.callback_query(F.data == "close_search")
async def close_search(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🔍 Поиск завершён.\n\n"
        "Выберите действие в меню ниже 👇",
        reply_markup=None
    )
    await callback.answer()

@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отменено")
    await callback.answer()

# ==================== ПОДПИСКА ИЗ ПОИСКА ====================

@router.callback_query(F.data == "subscribe_current")
async def subscribe_current(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    query = data.get("query")
    
    if not query:
        await callback.answer("❌ Нет активного поиска", show_alert=True)
        return
    
    # Проверяем лимит подписок
    count = await db.get_subscriptions_count(callback.from_user.id)
    if count >= config.MAX_SUBSCRIPTIONS:
        await callback.answer(
            f"⚠️ Максимум {config.MAX_SUBSCRIPTIONS} подписок",
            show_alert=True
        )
        return
    
    # Создаём подписку с текущими фильтрами
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

@router.callback_query(F.data == "vacancy_info")
async def vacancy_info(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    total = data.get("total", 0)
    loaded = len(data.get("vacancies", []))
    
    await callback.answer(
        f"Найдено: {total} вакансий\nЗагружено: {loaded}",
        show_alert=True
    )




