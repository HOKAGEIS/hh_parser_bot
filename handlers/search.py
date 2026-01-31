# search_router.py (полностью исправленная версия)

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
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
    viewing_results = State()
    entering_city = State()
    entering_salary = State()
    entering_exclude_word = State()
    writing_cover_letter = State()


# -------------------- helpers --------------------

def _vacancy_to_short_dict(v: Vacancy) -> Dict[str, Any]:
    return {
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


def _vacancy_from_short_dict(v: Dict[str, Any]) -> Vacancy:
    # Сигнатура соответствует вашему коду в back_to_list
    return Vacancy(
        id=v["id"],
        name=v["name"],
        url=v["url"],
        employer=v["employer"],
        employer_id=None,
        employer_logo=None,
        salary_from=v.get("salary_from"),
        salary_to=v.get("salary_to"),
        salary_currency=v.get("salary_currency"),
        city=v.get("city", ""),
        experience=v.get("experience", ""),
        schedule=v.get("schedule", ""),
        employment="",
        requirement=v.get("requirement"),
        responsibility=None,
        description=None,
        key_skills=[],
        published_at="",
        has_test=False,
        response_letter_required=False,
    )


async def _safe_edit_text(message, text: str, **kwargs) -> None:
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest as e:
        # Частая ситуация: пытаемся отредактировать на тот же текст
        if "message is not modified" in str(e):
            # если есть markup — попробуем обновить только его
            rm = kwargs.get("reply_markup")
            if rm is not None:
                try:
                    await message.edit_reply_markup(reply_markup=rm)
                except TelegramBadRequest:
                    pass
            return
        raise


async def _get_vacancy_at_index(state: FSMContext, index: int) -> Tuple[Optional[Vacancy], int]:
    """
    index — глобальный индекс вакансии: 0..total-1
    Достаём нужную страницу HH API, кешируем её в FSM и возвращаем одну вакансию + total.
    """
    data = await state.get_data()

    query = data.get("query")
    if not query:
        return None, 0

    per_page = int(data.get("per_page") or config.VACANCIES_PER_PAGE)
    if per_page <= 0:
        per_page = config.VACANCIES_PER_PAGE

    api_page = index // per_page
    offset = index % per_page

    cache_page = data.get("cache_page")
    cache_vacancies = data.get("cache_vacancies") or []
    total = int(data.get("total") or 0)

    if cache_page != api_page or not cache_vacancies:
        vacancies, total_api = await hh.search_vacancies(
            text=query,
            area=data.get("city"),
            experience=data.get("experience"),
            schedule=data.get("schedule"),
            salary=data.get("salary"),
            only_with_salary=data.get("only_with_salary", False),
            exclude_words=data.get("exclude_words", []),
            page=api_page,
            per_page=per_page,
        )
        total = int(total_api or 0)

        cache_vacancies = [_vacancy_to_short_dict(v) for v in vacancies]
        await state.update_data(cache_page=api_page, cache_vacancies=cache_vacancies, total=total)

    if offset < 0 or offset >= len(cache_vacancies):
        return None, total

    return _vacancy_from_short_dict(cache_vacancies[offset]), total


async def show_vacancy_message(message, vacancy: Vacancy, index: int, total: int, user_id: int, is_authorized: bool):
    """
    index — глобальный индекс (0..total-1)
    total — всего вакансий
    """
    is_fav = await db.is_favorite(user_id, vacancy.id)
    is_applied = await db.was_applied(user_id, vacancy.id)

    text = (
        f"📊 <b>Найдено: {total:,} вакансий</b>\n".replace(",", " ")
        + f"<i>Вакансия {index + 1} из {total:,}</i>\n\n".replace(",", " ")
        + vacancy.to_short_message()
    )

    await _safe_edit_text(
        message,
        text,
        reply_markup=kb.vacancy_kb(
            vacancy.id,
            is_fav,
            index,      # теперь это global index
            total,      # теперь это total вакансий (а не total_pages)
            is_applied,
            is_authorized,
        ),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


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
        parse_mode="HTML",
    )


@router.message(SearchStates.entering_query, F.text)
async def process_search_query(message: Message, state: FSMContext):
    query = (message.text or "").strip()
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
        current_index=0,
        total=0,
        per_page=config.VACANCIES_PER_PAGE,
        cache_page=None,
        cache_vacancies=[],
        city_variants={},
    )
    await state.set_state(None)

    # ✅ сохраняем в историю
    data = await state.get_data()
    await db.add_search_history(
        user_id=message.from_user.id,
        query=query,
        city=data.get("city"),
        city_name=data.get("city_name"),
        filters={
            "experience": data.get("experience"),
            "schedule": data.get("schedule"),
            "salary": data.get("salary"),
            "only_with_salary": data.get("only_with_salary"),
            "exclude_words": data.get("exclude_words"),
        },
    )

    await message.answer(
        f"🔍 Запрос: <b>{query}</b>\n\n"
        "Настройте фильтры или сразу начните поиск:",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )


# ==================== ФИЛЬТРЫ ====================

@router.callback_query(F.data == "back_to_filters")
async def back_to_filters(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()

    await _safe_edit_text(
        callback.message,
        f"🔍 Запрос: <b>{data.get('query')}</b>\n\n"
        "Настройте фильтры:",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )
    await callback.answer()


# ==================== ГОРОД ====================

@router.callback_query(F.data == "filter_city")
async def filter_city(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await _safe_edit_text(
        callback.message,
        "📍 <b>Выберите город</b>\n\n"
        "Выберите из списка или введите вручную:",
        reply_markup=kb.cities_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "enter_city_manual")
async def enter_city_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.entering_city)

    await _safe_edit_text(
        callback.message,
        "📍 <b>Введите название города:</b>\n\n"
        "<i>Например: Воронеж, Тюмень, Владивосток</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SearchStates.entering_city, F.text)
async def process_city_input(message: Message, state: FSMContext):
    city_name = (message.text or "").strip()
    if len(city_name) < 2:
        await message.answer("⚠️ Слишком короткое название")
        return

    await message.answer("🔍 Ищу город...")

    cities = await hh.search_area(city_name)
    if not cities:
        # остаёмся в entering_city, чтобы пользователь мог сразу ввести другой город
        await message.answer(
            f"😔 Город «{city_name}» не найден.\n\n"
            "Попробуйте другое название:",
            reply_markup=kb.back_kb("filter_city"),
        )
        return

    if len(cities) == 1:
        city = cities[0]
        name = city.get("text", city.get("name"))
        await state.update_data(city=str(city.get("id")), city_name=name)
        await state.set_state(None)

        data = await state.get_data()
        await message.answer(
            f"✅ Выбран город: <b>{name}</b>\n\n"
            f"🔍 Запрос: <b>{data.get('query')}</b>",
            reply_markup=kb.filters_kb(data),
            parse_mode="HTML",
        )
        return

    # Несколько результатов — сохраняем id->name и показываем выбор
    variants = {str(c.get("id")): c.get("text", c.get("name")) for c in cities}
    await state.update_data(city_variants=variants)
    await state.set_state(None)

    await message.answer(
        f"📍 Найдено несколько городов по запросу «{city_name}»:\n\n"
        "Выберите нужный:",
        reply_markup=kb.found_cities_kb(cities),  # ВАЖНО: кнопки должны быть set_city_{id} (без названия!)
    )


@router.message(SearchStates.entering_city)
async def process_city_input_not_text(message: Message, state: FSMContext):
    await message.answer("⚠️ Пожалуйста, введите название города текстом")


@router.callback_query(F.data.startswith("set_city_"))
async def set_city(callback: CallbackQuery, state: FSMContext):
    # Ожидаемый формат:
    # - set_city_any
    # - set_city_{id}
    payload = callback.data.replace("set_city_", "", 1)

    if payload == "any":
        await state.update_data(city=None, city_name=None)
        city_display = "Любой"
    else:
        city_id = payload
        data = await state.get_data()
        city_name = (data.get("city_variants") or {}).get(str(city_id), f"ID {city_id}")
        await state.update_data(city=str(city_id), city_name=city_name)
        city_display = city_name

    data = await state.get_data()
    await _safe_edit_text(
        callback.message,
        f"✅ Город: <b>{city_display}</b>\n\n"
        f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )
    await callback.answer(f"✅ Выбрано: {city_display}")


# ==================== ЗАРПЛАТА ====================

@router.callback_query(F.data == "filter_salary")
async def filter_salary(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await _safe_edit_text(
        callback.message,
        "💰 <b>Минимальная зарплата</b>\n\n"
        "Выберите или введите свою сумму:",
        reply_markup=kb.salary_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "enter_salary_manual")
async def enter_salary_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.entering_salary)
    await _safe_edit_text(
        callback.message,
        "💰 <b>Введите минимальную зарплату</b>\n\n"
        "Введите число (только цифры):\n\n"
        "<i>Например: 80000, 150000, 250000</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SearchStates.entering_salary, F.text)
async def process_salary_input(message: Message, state: FSMContext):
    raw = message.text or ""
    salary_text = "".join(filter(str.isdigit, raw))

    if not salary_text:
        await message.answer("⚠️ Введите число. Например: 100000")
        return

    try:
        salary = int(salary_text)
    except ValueError:
        await message.answer("⚠️ Введите число. Например: 100000")
        return

    if salary < 1000:
        await message.answer("⚠️ Слишком маленькая сумма. Введите в рублях (например: 50000)")
        return
    if salary > 10_000_000:
        await message.answer("⚠️ Слишком большая сумма. Максимум 10 000 000")
        return

    await state.update_data(salary=salary)
    await state.set_state(None)

    data = await state.get_data()
    await message.answer(
        f"✅ Зарплата: от <b>{salary:,}₽</b>\n\n".replace(",", " ")
        + f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )


@router.message(SearchStates.entering_salary)
async def process_salary_input_not_text(message: Message, state: FSMContext):
    await message.answer("⚠️ Введите число")


@router.callback_query(F.data.startswith("set_salary_"))
async def set_salary(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)

    salary_str = callback.data.replace("set_salary_", "", 1)
    if salary_str == "any":
        salary = None
        salary_display = "Любая"
    else:
        try:
            salary = int(salary_str)
        except ValueError:
            await callback.answer("Ошибка суммы", show_alert=True)
            return
        salary_display = f"от {salary:,}₽".replace(",", " ")

    await state.update_data(salary=salary)
    data = await state.get_data()

    await _safe_edit_text(
        callback.message,
        f"✅ Зарплата: <b>{salary_display}</b>\n\n"
        f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )
    await callback.answer(f"✅ {salary_display}")


# ==================== ИСКЛЮЧЕНИЯ ====================

@router.callback_query(F.data == "filter_exclude")
async def filter_exclude(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)

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

    await _safe_edit_text(
        callback.message,
        text,
        reply_markup=kb.exclude_words_kb(words),  # ВАЖНО: удаление должно быть remove_exclude_{index}
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "add_exclude_word")
async def add_exclude_word(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.entering_exclude_word)
    await _safe_edit_text(
        callback.message,
        "🚫 <b>Добавить слово-исключение</b>\n\n"
        "Введите слово или фразу для исключения:\n\n"
        "<i>Например: стажёр, без опыта, junior</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SearchStates.entering_exclude_word, F.text)
async def process_exclude_word(message: Message, state: FSMContext):
    word = (message.text or "").strip().lower()
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
        parse_mode="HTML",
    )


@router.message(SearchStates.entering_exclude_word)
async def process_exclude_word_not_text(message: Message, state: FSMContext):
    await message.answer("⚠️ Введите слово текстом")


@router.callback_query(F.data.startswith("remove_exclude_"))
async def remove_exclude_word(callback: CallbackQuery, state: FSMContext):
    # Ожидаемый формат: remove_exclude_{index}
    idx_str = callback.data.replace("remove_exclude_", "", 1)

    data = await state.get_data()
    words = data.get("exclude_words", [])

    try:
        idx = int(idx_str)
    except ValueError:
        await callback.answer("Ошибка кнопки", show_alert=True)
        return

    if 0 <= idx < len(words):
        removed = words.pop(idx)
        await state.update_data(exclude_words=words)
        await callback.answer(f"✅ Удалено: {removed}")
    else:
        await callback.answer("Уже удалено", show_alert=False)

    await _safe_edit_text(
        callback.message,
        "🚫 <b>Слова-исключения</b>\n\n" +
        (", ".join([f"<code>{w}</code>" for w in words]) if words else "Список пуст"),
        reply_markup=kb.exclude_words_kb(words),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "clear_exclude_words")
async def clear_exclude_words(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await state.update_data(exclude_words=[])

    await _safe_edit_text(
        callback.message,
        "🚫 <b>Слова-исключения</b>\n\n"
        "Список очищен.",
        reply_markup=kb.exclude_words_kb([]),
        parse_mode="HTML",
    )
    await callback.answer("🗑 Список очищен")


# ==================== ОПЫТ И ГРАФИК ====================

@router.callback_query(F.data == "filter_experience")
async def filter_experience(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await _safe_edit_text(
        callback.message,
        "💼 <b>Требуемый опыт работы:</b>",
        reply_markup=kb.experience_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_exp_"))
async def set_experience(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)

    exp = callback.data.replace("set_exp_", "", 1)
    if exp == "any":
        exp = None

    await state.update_data(experience=exp)
    data = await state.get_data()

    await _safe_edit_text(
        callback.message,
        f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )
    await callback.answer("✅ Опыт выбран")


@router.callback_query(F.data == "filter_schedule")
async def filter_schedule(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await _safe_edit_text(
        callback.message,
        "⏰ <b>График работы:</b>",
        reply_markup=kb.schedule_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_schedule_"))
async def set_schedule(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)

    schedule = callback.data.replace("set_schedule_", "", 1)
    if schedule == "any":
        schedule = None

    await state.update_data(schedule=schedule)
    data = await state.get_data()

    await _safe_edit_text(
        callback.message,
        f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )
    await callback.answer("✅ График выбран")


@router.callback_query(F.data == "filter_reset")
async def reset_filters(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)

    await state.update_data(
        city=None,
        city_name=None,
        experience=None,
        schedule=None,
        salary=None,
        exclude_words=[],
    )

    data = await state.get_data()
    await _safe_edit_text(
        callback.message,
        f"🔄 Фильтры сброшены\n\n"
        f"🔍 Запрос: <b>{data.get('query')}</b>",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )
    await callback.answer("🔄 Сброшено")


# ==================== ПОИСК ====================

@router.callback_query(F.data == "search_now")
async def execute_search(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("query"):
        await callback.answer("⚠️ Сначала введите поисковый запрос", show_alert=True)
        return

    await _safe_edit_text(callback.message, "🔍 Ищу вакансии...")

    per_page = int(data.get("per_page") or config.VACANCIES_PER_PAGE)

    vacancies, total = await hh.search_vacancies(
        text=data.get("query"),
        area=data.get("city"),
        experience=data.get("experience"),
        schedule=data.get("schedule"),
        salary=data.get("salary"),
        only_with_salary=data.get("only_with_salary", False),
        exclude_words=data.get("exclude_words", []),
        page=0,
        per_page=per_page,
    )

    if not vacancies:
        await _safe_edit_text(
            callback.message,
            "😔 Ничего не найдено.\n\n"
            "Попробуйте:\n"
            "• Изменить запрос\n"
            "• Сбросить фильтры\n"
            "• Убрать слова-исключения",
            reply_markup=kb.filters_kb(data),
        )
        await callback.answer()
        return

    cache_vacancies = [_vacancy_to_short_dict(v) for v in vacancies]

    await state.update_data(
        current_index=0,
        total=int(total or 0),
        cache_page=0,
        cache_vacancies=cache_vacancies,
    )
    await state.set_state(SearchStates.viewing_results)

    user = await db.get_user(callback.from_user.id)
    is_authorized = bool(user and user.hh_access_token)

    first = _vacancy_from_short_dict(cache_vacancies[0])
    await show_vacancy_message(
        callback.message,
        first,
        index=0,
        total=int(total or 0),
        user_id=callback.from_user.id,
        is_authorized=is_authorized,
    )
    await callback.answer()


# ==================== НАВИГАЦИЯ ====================

@router.callback_query(SearchStates.viewing_results, F.data.startswith("page_"))
async def change_page(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if callback.data == "page_info":
        total = int(data.get("total") or 0)
        current_index = int(data.get("current_index") or 0)
        if total <= 0:
            await callback.answer("Нет данных", show_alert=True)
            return
        await callback.answer(
            f"Вакансия {current_index + 1} из {total:,}".replace(",", " "),
            show_alert=True,
        )
        return

    try:
        index = int(callback.data.replace("page_", "", 1))
    except ValueError:
        await callback.answer("Ошибка страницы", show_alert=True)
        return

    total = int(data.get("total") or 0)
    if total and (index < 0 or index >= total):
        await callback.answer("Больше вакансий нет")
        return

    await _safe_edit_text(callback.message, "🔄 Загружаю...")

    vacancy, total2 = await _get_vacancy_at_index(state, index)
    if not vacancy:
        await callback.answer("Больше вакансий нет")
        return

    await state.update_data(current_index=index, total=total2)

    user = await db.get_user(callback.from_user.id)
    is_authorized = bool(user and user.hh_access_token)

    await show_vacancy_message(callback.message, vacancy, index, total2, callback.from_user.id, is_authorized)
    await callback.answer()


# ==================== ПОЛНОЕ ОПИСАНИЕ ====================

import logging
log = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("full_"))
async def show_full_vacancy(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.replace("full_", "", 1)

    await _safe_edit_text(callback.message, "📄 Загружаю полное описание...")

    vacancy = await hh.get_vacancy_full(vacancy_id)
    if not vacancy:
        await callback.answer("❌ Не удалось загрузить вакансию", show_alert=True)
        return

    user = await db.get_user(callback.from_user.id)
    is_authorized = bool(user and getattr(user, "hh_access_token", None))
    is_applied = await db.was_applied(callback.from_user.id, vacancy_id)

    # 1) Если hh.get_vacancy_full вернул dict/что-то не то — не падаем
    if not hasattr(vacancy, "to_full_message"):
        log.error("get_vacancy_full(%s) returned %s: %r", vacancy_id, type(vacancy), vacancy)
        await _safe_edit_text(
            callback.message,
            "❌ Ошибка формата данных вакансии (нет to_full_message).\n\n"
            "Попробуйте позже или откройте вакансию на hh.ru.",
            reply_markup=kb.vacancy_full_kb(vacancy_id, is_authorized, is_applied),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        await callback.answer("Ошибка данных", show_alert=True)
        return

    # 2) Если внутри to_full_message что-то упало — тоже не падаем
    try:
        text = vacancy.to_full_message()
    except Exception as e:
        log.exception("to_full_message failed for vacancy_id=%s: %s", vacancy_id, e)
        # фолбек на короткое сообщение
        if hasattr(vacancy, "to_short_message"):
            text = "⚠️ Полное описание временно недоступно.\n\n" + vacancy.to_short_message()
        else:
            text = "⚠️ Полное описание временно недоступно."

    if len(text) > 4000:
        text = text[:4000] + "\n\n<i>...текст обрезан. Откройте на hh.ru для полной версии</i>"

    await _safe_edit_text(
        callback.message,
        text,
        reply_markup=kb.vacancy_full_kb(vacancy_id, is_authorized, is_applied),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer()

# ==================== ИЗБРАННОЕ ====================

async def _refresh_current_markup(callback: CallbackQuery, state: FSMContext, vacancy_id: str):
    data = await state.get_data()
    total = int(data.get("total") or 0)
    current_index = int(data.get("current_index") or 0)

    user = await db.get_user(callback.from_user.id)
    is_authorized = bool(user and user.hh_access_token)

    is_fav = await db.is_favorite(callback.from_user.id, vacancy_id)
    is_applied = await db.was_applied(callback.from_user.id, vacancy_id)

    try:
        await callback.message.edit_reply_markup(
            reply_markup=kb.vacancy_kb(
                vacancy_id,
                is_fav,
                current_index,
                total,
                is_applied,
                is_authorized,
            )
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("fav_"))
async def add_to_fav(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.replace("fav_", "", 1)

    # Пытаемся сохранить данные вакансии из кеша (если есть)
    data = await state.get_data()
    vacancy_data = None
    for v in (data.get("cache_vacancies") or []):
        if v.get("id") == vacancy_id:
            vacancy_data = v
            break

    if vacancy_data:
        await db.add_favorite(callback.from_user.id, vacancy_id, vacancy_data)
        await callback.answer("⭐ Добавлено в избранное!")
        await _refresh_current_markup(callback, state, vacancy_id)
    else:
        # Даже без данных — хотя бы отметим
        await db.add_favorite(callback.from_user.id, vacancy_id, {"id": vacancy_id})
        await callback.answer("⭐ Добавлено в избранное!")
        await _refresh_current_markup(callback, state, vacancy_id)


@router.callback_query(F.data.startswith("unfav_"))
async def remove_from_fav(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.replace("unfav_", "", 1)
    await db.remove_favorite(callback.from_user.id, vacancy_id)
    await callback.answer("💔 Удалено из избранного")
    await _refresh_current_markup(callback, state, vacancy_id)


# ==================== ПОДПИСКА ИЗ ПОИСКА ====================

@router.callback_query(F.data == "subscribe_current")
async def subscribe_from_search(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    count = await db.get_subscriptions_count(callback.from_user.id)
    if count >= config.MAX_SUBSCRIPTIONS:
        await callback.answer(f"⚠️ Максимум {config.MAX_SUBSCRIPTIONS} подписок", show_alert=True)
        return

    query = data.get("query")
    if not query:
        await callback.answer("⚠️ Нет активного поиска", show_alert=True)
        return

    await db.add_subscription(
        user_id=callback.from_user.id,
        query=query,
        city=data.get("city"),
        city_name=data.get("city_name"),
        experience=data.get("experience"),
        schedule=data.get("schedule"),
        min_salary=data.get("salary"),
        exclude_words=data.get("exclude_words", []),
    )

    await callback.answer(f"🔔 Подписка на «{query}» создана!", show_alert=True)


# ==================== ЗАКРЫТЬ / ОТМЕНА ====================

@router.callback_query(F.data == "close_search")
async def close_search(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _safe_edit_text(callback.message, "❌ Отменено")
    await callback.answer()


# ==================== FALLBACK (чтобы не было Update is not handled) ====================

@router.callback_query(SearchStates.viewing_results)
async def unknown_callback_in_results(callback: CallbackQuery):
    await callback.answer("Кнопка неактуальна или не поддерживается.", show_alert=False)


@router.message(SearchStates.viewing_results)
async def unknown_message_in_results(message: Message, state: FSMContext):
    await message.answer("Используйте кнопки навигации под вакансией или нажмите ❌ Закрыть.")

# ==================== ИСТОРИЯ ПОИСКА (кнопка меню) ====================

@router.message(F.text == "🕐 История поиска")
async def show_search_history_menu(message: Message, state: FSMContext):
    await state.clear()
    history = await db.get_search_history(message.from_user.id, limit=10)

    text = "🕐 <b>История поиска</b>\n\n"
    text += "Выберите запрос:" if history else "История пуста."

    await message.answer(
        text,
        reply_markup=kb.search_history_kb(history),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "history_empty")
async def history_empty(callback: CallbackQuery):
    await callback.answer("История пуста", show_alert=True)


@router.callback_query(F.data == "clear_history")
async def clear_history(callback: CallbackQuery):
    await db.clear_search_history(callback.from_user.id)

    await callback.message.edit_text(
        "🕐 <b>История поиска</b>\n\n✅ История очищена.",
        reply_markup=kb.search_history_kb([]),
        parse_mode="HTML",
    )
    await callback.answer("🗑 Очищено")


@router.callback_query(F.data.startswith("repeat_search_"))
async def repeat_search_from_history(callback: CallbackQuery, state: FSMContext):
    idx_str = callback.data.replace("repeat_search_", "", 1)
    try:
        idx = int(idx_str)
    except ValueError:
        await callback.answer("Ошибка", show_alert=True)
        return

    history = await db.get_search_history(callback.from_user.id, limit=10)
    if idx < 0 or idx >= len(history):
        await callback.answer("Запрос не найден", show_alert=True)
        return

    item = history[idx]
    query = (item.get("query") or "").strip()
    if not query:
        await callback.answer("Пустой запрос", show_alert=True)
        return

    user = await db.get_user(callback.from_user.id)
    filters = item.get("filters") or {}

    await state.clear()
    await state.update_data(
        query=query,
        city=item.get("city") or (user.default_city if user else None),
        city_name=item.get("city_name") or (user.default_city_name if user else None),
        experience=filters.get("experience") or (user.default_experience if user else None),
        schedule=filters.get("schedule") or (user.default_schedule if user else None),
        salary=filters.get("salary") or (user.min_salary if user else None),
        only_with_salary=filters.get("only_with_salary") if "only_with_salary" in filters else (user.only_with_salary if user else False),
        exclude_words=filters.get("exclude_words") or (user.exclude_words if user else []),
        current_index=0,
        total=0,
        per_page=config.VACANCIES_PER_PAGE,
        cache_page=None,
        cache_vacancies=[],
        city_variants={},
    )
    await state.set_state(None)

    data = await state.get_data()
    await callback.message.edit_text(
        f"🔍 Запрос: <b>{query}</b>\n\n"
        "Настройте фильтры или сразу начните поиск:",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )
    await callback.answer("✅ Загружено")


