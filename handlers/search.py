# handlers/search.py (ПОЛНОСТЬЮ ИСПРАВЛЕННЫЙ - ФИНАЛЬНАЯ ВЕРСИЯ)
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

import database as db
import keyboards as kb
from hh_api import hh, Vacancy
from config import Config
import logging

router = Router()
logger = logging.getLogger(__name__)


class SearchStates(StatesGroup):
    entering_query = State()
    viewing_results = State()
    entering_city = State()
    entering_salary = State()
    entering_exclude_word = State()
    writing_cover_letter = State()
    waiting_location = State()  # ← ДОБАВЛЕНО


# ==================== HELPERS ====================

import re
import html


def _hh_html_to_text(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)<p>", "\n", s)
    s = re.sub(r"(?i)</li>", "\n", s)
    s = re.sub(r"(?i)<li>", "• ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"\n{3,}", "\n\n", s.strip())
    return s


def _format_salary_dict(sal: dict | None) -> str:
    if not sal:
        return ""
    frm = sal.get("from")
    to = sal.get("to")
    cur = sal.get("currency") or "RUR"
    cur_map = {"RUR": "₽", "RUB": "₽", "USD": "$", "EUR": "€", "KZT": "₸"}
    cur_sym = cur_map.get(cur, cur)
    if frm and to:
        return f"{frm:,}–{to:,}{cur_sym}".replace(",", " ")
    if frm:
        return f"от {frm:,}{cur_sym}".replace(",", " ")
    if to:
        return f"до {to:,}{cur_sym}".replace(",", " ")
    return f"{cur_sym}"


def _format_salary_obj(v) -> str:
    frm = getattr(v, "salary_from", None)
    to = getattr(v, "salary_to", None)
    cur = getattr(v, "salary_currency", None) or "RUR"
    cur_map = {"RUR": "₽", "RUB": "₽", "USD": "$", "EUR": "€", "KZT": "₸"}
    cur_sym = cur_map.get(cur, cur)
    if frm and to:
        return f"{frm:,}–{to:,}{cur_sym}".replace(",", " ")
    if frm:
        return f"от {frm:,}{cur_sym}".replace(",", " ")
    if to:
        return f"до {to:,}{cur_sym}".replace(",", " ")
    return ""


async def _safe_edit_text(message, text, reply_markup=None, parse_mode=None, disable_web_page_preview=None):
    try:
        return await message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview
        )
    except TelegramBadRequest:
        return await message.answer(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )


def _vacancy_to_short_dict(vacancy):
    return {
        "id": getattr(vacancy, "id", ""),
        "name": getattr(vacancy, "name", ""),
        "employer": getattr(vacancy, "employer", ""),
        "salary": _format_salary_obj(vacancy),
        "url": getattr(vacancy, "url", ""),
        "city": getattr(vacancy, "city", ""),
        "experience": getattr(vacancy, "experience", ""),
        "schedule": getattr(vacancy, "schedule", ""),
    }


def _vacancy_from_short_dict(data):
    class TempVacancy:
        def __init__(self, data):
            for key, value in data.items():
                setattr(self, key, value)
    return TempVacancy(data)


async def _get_vacancy_at_index(state: FSMContext, index: int):
    data = await state.get_data()
    cache_vacancies = data.get("cache_vacancies", [])
    total = data.get("total", 0)

    if index < len(cache_vacancies):
        return _vacancy_from_short_dict(cache_vacancies[index]), total

    page = index // Config.VACANCIES_PER_PAGE
    per_page = Config.VACANCIES_PER_PAGE
    search_data = {k: v for k, v in data.items() if k in ("query", "city", "experience", "schedule", "salary", "only_with_salary", "exclude_words")}

    vacancies, total = await hh.search_vacancies(
        text=search_data.get("query"),
        area=search_data.get("city"),
        experience=search_data.get("experience"),
        schedule=search_data.get("schedule"),
        salary=search_data.get("salary"),
        only_with_salary=search_data.get("only_with_salary", False),
        exclude_words=search_data.get("exclude_words", []),
        page=page,
        per_page=per_page,
    )

    new_cache = [_vacancy_to_short_dict(v) for v in vacancies]
    await state.update_data(cache_page=page, cache_vacancies=new_cache, total=total)

    target_idx = index % Config.VACANCIES_PER_PAGE
    if target_idx < len(new_cache):
        return _vacancy_from_short_dict(new_cache[target_idx]), total

    return None, total


async def _show_vacancy(message, vacancy, index: int, total: int, user_id: int, is_authorized: bool):
    salary = getattr(vacancy, "salary", "")
    city = getattr(vacancy, "city", "")
    experience = getattr(vacancy, "experience", "")
    schedule = getattr(vacancy, "schedule", "")

    text = f"<b>{vacancy.name}</b>\n\n"
    text += f"<b>Компания:</b> {vacancy.employer}\n"
    text += f"<b>Город:</b> {city}\n"
    text += f"<b>Зарплата:</b> {salary}\n"
    text += f"<b>Опыт:</b> {experience}\n"
    text += f"<b>График:</b> {schedule}\n\n"
    text += f'<a href="{vacancy.url}">🔗 Ссылка на вакансию</a>'

    is_fav = await db.is_favorite(user_id, vacancy.id)
    is_applied = await db.was_applied(user_id, vacancy.id)

    await _safe_edit_text(
        message,
        text,
        reply_markup=kb.vacancy_kb(
            vacancy_id=vacancy.id,
            is_fav=is_fav,
            current_index=index,
            total=total,
            is_applied=is_applied,
            is_authorized=is_authorized,
        ),
        parse_mode="HTML",
        disable_web_page_preview=True
    )


# ==================== ПОИСК ====================

@router.message(F.text == "🔍 Поиск вакансий")
async def start_search(message: Message, state: FSMContext):
    await db.ensure_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    await state.clear()
    await state.set_state(SearchStates.entering_query)
    await message.answer(
        "<b>🔍 Поиск вакансий</b>\n\n"
        "Введите ключевые слова для поиска:\n"
        "<i>Например: Python, UX/UI дизайнер, менеджер продаж</i>",
        parse_mode="HTML",
    )


@router.message(SearchStates.entering_query, F.text)
async def process_search_query(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer("❌ Запрос слишком короткий. Минимум 2 символа.")
        return

    user_settings = await db.get_user_settings(message.from_user.id)

    await state.update_data(
        query=query,
        city=user_settings.get("city_id"),
        city_name=user_settings.get("city_name"),
        experience=user_settings.get("experience"),
        schedule=user_settings.get("schedule"),
        salary=user_settings.get("salary_from"),
        only_with_salary=user_settings.get("only_with_salary", False),
        exclude_words=user_settings.get("exclude_words", []),
        current_index=0,
        total=0,
        per_page=Config.VACANCIES_PER_PAGE,
        cache_page=None,
        cache_vacancies=[],
        city_variants={},
    )

    await state.set_state(None)
    data = await state.get_data()

    await db.save_search_query(
        user_id=message.from_user.id,
        query=query,
        filters={
            "experience": data.get("experience"),
            "schedule": data.get("schedule"),
            "salary": data.get("salary"),
            "only_with_salary": data.get("only_with_salary"),
            "exclude_words": data.get("exclude_words"),
        }
    )

    await message.answer(
        f"<b>Поиск:</b> {query}\n\n"
        "Настройте фильтры или начните поиск:",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )


# ==================== ФИЛЬТРЫ ====================

@router.callback_query(F.data == "back_to_filters")
async def back_to_filters(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()
    query = data.get("query", "")

    if not query:
        await callback.answer("❌ Запрос не найден", show_alert=True)
        return

    await _safe_edit_text(
        callback.message,
        f"<b>Поиск:</b> {query}\n\nНастройте фильтры:",
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
        "<b>📍 Выбор города</b>\n\n"
        "Выберите способ указания города:",
        reply_markup=kb.cities_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "enter_city_manual")
async def enter_city_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.entering_city)
    await _safe_edit_text(
        callback.message,
        "<b>✏️ Введите название города</b>\n\n"
        "<i>Например: Москва, Санкт-Петербург, Новосибирск</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SearchStates.entering_city, F.text & ~F.text.startswith("/"))
async def process_city_input(message: Message, state: FSMContext):
    city_name = (message.text or "").strip()

    if len(city_name) < 2:
        await message.answer("❌ Название слишком короткое")
        return

    searching_msg = await message.answer("🔍 Ищу город...")
    cities = await hh.search_area(city_name)

    try:
        await searching_msg.delete()
    except:
        pass

    if not cities:
        await message.answer(
            f"❌ Город \"{city_name}\" не найден. Попробуйте другое название.",
            reply_markup=kb.back_kb("back_to_filters"),
        )
        return

    if len(cities) == 1:
        city = cities[0]
        name = city.get("text") or city.get("name")
        await state.update_data(city=str(city.get("id")), city_name=name)
        await state.set_state(None)

        data = await state.get_data()

        await message.answer(
            f"<b>Выбран город:</b> {name}\n\n"
            f"<b>Поиск:</b> {data.get('query')}",
            reply_markup=kb.filters_kb(data),
            parse_mode="HTML",
        )
        return

    variants = {str(c.get("id")): (c.get("text") or c.get("name")) for c in cities[:10]}
    await state.update_data(city_variants=variants)
    await state.set_state(None)

    await message.answer(
        f"Найдено несколько вариантов для \"{city_name}\":",
        reply_markup=kb.found_cities_kb(cities[:10]),
    )


@router.message(SearchStates.entering_city)
async def process_city_input_not_text(message: Message, state: FSMContext):
    if message.text:
        await state.set_state(None)
        data = await state.get_data()
        await message.answer(
            f"<b>Поиск:</b> {data.get('query')}",
            reply_markup=kb.filters_kb(data),
            parse_mode="HTML",
        )
    else:
        await message.answer("❌ Пожалуйста, отправьте текст")


@router.callback_query(F.data.startswith("set_city_"))
async def set_city(callback: CallbackQuery, state: FSMContext):
    payload = callback.data.replace("set_city_", "", 1)

    if payload == "any":
        await state.update_data(city=None, city_name=None)
        city_display = "Любой"
    else:
        city_id = payload
        data = await state.get_data()

        if hasattr(Config, "POPULAR_CITIES") and city_id in Config.POPULAR_CITIES:
            city_name = Config.POPULAR_CITIES[city_id]
        else:
            city_name = (data.get("city_variants") or {}).get(str(city_id), f"ID {city_id}")

        await state.update_data(city=str(city_id), city_name=city_name)
        city_display = city_name

    data = await state.get_data()

    await _safe_edit_text(
        callback.message,
        f"<b>Выбран город:</b> {city_display}\n\n"
        f"<b>Поиск:</b> {data.get('query')}",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )
    await callback.answer(f"✅ Город: {city_display}")


# ==================== ГЕОЛОКАЦИЯ (ИСПРАВЛЕНО) ====================

@router.callback_query(F.data == "request_location")
async def request_location(callback: CallbackQuery, state: FSMContext):
    """Запрос геолокации"""
    await state.set_state(SearchStates.waiting_location)
    logger.info(f"User {callback.from_user.id} requested location")

    await callback.message.answer(
        "<b>📍 Определение города по геолокации</b>\n\n"
        "Нажмите кнопку ниже, чтобы отправить своё местоположение.",
        reply_markup=kb.location_request_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SearchStates.waiting_location, F.text == "❌ Отмена")
async def cancel_location_request(message: Message, state: FSMContext):
    """Обработка кнопки Отмена при запросе геолокации"""
    logger.info(f"User {message.from_user.id} cancelled location request")

    # ВАЖНО: Получаем данные ПЕРЕД сбросом состояния
    data = await state.get_data()
    query = data.get("query", "")

    # Сбрасываем состояние
    await state.set_state(None)

    # Удаляем ReplyKeyboard
    await message.answer(
        "❌ Отменено",
        reply_markup=ReplyKeyboardRemove()
    )

    # Проверяем наличие активного поиска
    if query:
        # Если есть активный поиск - возвращаем к фильтрам
        await message.answer(
            f"<b>Поиск:</b> {query}\n\n"
            "Настройте фильтры или начните поиск:",
            reply_markup=kb.filters_kb(data),
            parse_mode="HTML",
        )
    else:
        # Если поиска нет - возвращаем в главное меню
        await message.answer(
            "Выберите действие:",
            reply_markup=kb.main_menu_kb(message.from_user.id)
        )


@router.message(SearchStates.waiting_location, F.location)
async def process_location(message: Message, state: FSMContext):
    """Обработка полученной геолокации"""
    lat = message.location.latitude
    lon = message.location.longitude
    logger.info(f"User {message.from_user.id} sent location: {lat}, {lon}")

    await state.set_state(None)

    await message.answer(
        "📍 Получена геолокация. Определяю город...",
        reply_markup=ReplyKeyboardRemove()
    )

    # TODO: Здесь должна быть логика определения города по координатам
    await message.answer(
        "❌ Определение города по геолокации временно недоступно. "
        "Выберите город из списка или введите вручную.",
        reply_markup=kb.back_kb("back_to_filters")
    )


# ==================== ЗАРПЛАТА ====================

@router.callback_query(F.data == "filter_salary")
async def filter_salary(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await _safe_edit_text(
        callback.message,
        "<b>💰 Минимальная зарплата</b>\n\n"
        "Выберите минимальную желаемую зарплату:",
        reply_markup=kb.salary_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "enter_salary_manual")
async def enter_salary_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.entering_salary)
    await _safe_edit_text(
        callback.message,
        "<b>💰 Введите минимальную зарплату</b>\n\n"
        "<i>Примеры: 80000, 150000, 250000</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SearchStates.entering_salary, F.text)
async def process_salary_input(message: Message, state: FSMContext):
    raw = message.text or ""
    salary_text = "".join(filter(str.isdigit, raw))

    if not salary_text:
        await message.answer("❌ Введите число. Например: 100000")
        return

    try:
        salary = int(salary_text)
    except ValueError:
        await message.answer("❌ Некорректное число. Например: 100000")
        return

    if salary < 1000:
        await message.answer("❌ Слишком маленькая зарплата. Минимум 50000")
        return

    if salary > 10000000:
        await message.answer("❌ Слишком большая зарплата. Максимум 10 000 000")
        return

    await state.update_data(salary=salary)
    await state.set_state(None)

    data = await state.get_data()

    await message.answer(
        f"<b>Минимальная зарплата:</b> {salary:,}₽".replace(",", " ") + "\n\n"
        f"<b>Поиск:</b> {data.get('query')}",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )


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
            await callback.answer("❌ Ошибка", show_alert=True)
            return
        salary_display = f"от {salary:,}₽".replace(",", " ")

    await state.update_data(salary=salary)
    data = await state.get_data()

    await _safe_edit_text(
        callback.message,
        f"<b>Минимальная зарплата:</b> {salary_display}\n\n"
        f"<b>Поиск:</b> {data.get('query')}",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )
    await callback.answer(f"✅ Зарплата: {salary_display}")


# ==================== СЛОВА-ИСКЛЮЧЕНИЯ ====================

@router.callback_query(F.data == "filter_exclude")
async def filter_exclude(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()
    words = data.get("exclude_words", [])

    text = "<b>🚫 Слова-исключения</b>\n\n"
    if words:
        text += "Текущий список:\n"
        text += "\n".join([f"<code>{w}</code>" for w in words])
        text += "\n\nНажмите на слово чтобы удалить."
    else:
        text += "Список пуст. Добавьте слова, которые хотите исключить из поиска.\n\n"
        text += "<i>Например: junior, стажер, удаленка</i>"

    await _safe_edit_text(
        callback.message,
        text,
        reply_markup=kb.exclude_words_kb(words),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "add_exclude_word")
async def add_exclude_word(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.entering_exclude_word)
    await _safe_edit_text(
        callback.message,
        "<b>➕ Добавить слово-исключение</b>\n\n"
        "Введите слово, которое нужно исключить из поиска:\n"
        "<i>Например: junior, стажер, intern</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SearchStates.entering_exclude_word, F.text)
async def process_exclude_word(message: Message, state: FSMContext):
    word = (message.text or "").strip().lower()

    if len(word) < 2:
        await message.answer("❌ Слово слишком короткое")
        return

    if len(word) > 50:
        await message.answer("❌ Слово слишком длинное. Максимум 50 символов")
        return

    data = await state.get_data()
    words = data.get("exclude_words", [])

    if len(words) >= Config.MAX_EXCLUDE_WORDS:
        await message.answer(f"❌ Максимум {Config.MAX_EXCLUDE_WORDS} слов-исключений")
        return

    if word not in words:
        words.append(word)

    await state.update_data(exclude_words=words)
    await state.set_state(None)

    await message.answer(
        f"<b>✅ Добавлено:</b> {word}\n\n"
        f"Всего слов-исключений: {len(words)}",
        reply_markup=kb.exclude_words_kb(words),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("remove_exclude_"))
async def remove_exclude_word(callback: CallbackQuery, state: FSMContext):
    idx_str = callback.data.replace("remove_exclude_", "", 1)
    data = await state.get_data()
    words = data.get("exclude_words", [])

    try:
        idx = int(idx_str)
    except ValueError:
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    if 0 <= idx < len(words):
        removed = words.pop(idx)
        await state.update_data(exclude_words=words)
        await callback.answer(f"✅ Удалено: {removed}")
    else:
        await callback.answer("❌ Слово не найдено", show_alert=False)

    await _safe_edit_text(
        callback.message,
        "<b>🚫 Слова-исключения</b>\n\n" +
        ("\n".join([f"<code>{w}</code>" for w in words]) if words else "Список пуст"),
        reply_markup=kb.exclude_words_kb(words),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "clear_exclude_words")
async def clear_exclude_words(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await state.update_data(exclude_words=[])

    await _safe_edit_text(
        callback.message,
        "<b>🚫 Слова-исключения</b>\n\n"
        "Список очищен.",
        reply_markup=kb.exclude_words_kb([]),
        parse_mode="HTML",
    )
    await callback.answer("✅ Список очищен")


# ==================== ОПЫТ / ГРАФИК ====================

@router.callback_query(F.data == "filter_experience")
async def filter_experience(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await _safe_edit_text(
        callback.message,
        "<b>💼 Опыт работы</b>\n\n"
        "Выберите требуемый опыт:",
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
        f"<b>Поиск:</b> {data.get('query')}",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "filter_schedule")
async def filter_schedule(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await _safe_edit_text(
        callback.message,
        "<b>⏰ График работы</b>\n\n"
        "Выберите желаемый график:",
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
        f"<b>Поиск:</b> {data.get('query')}",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )
    await callback.answer()


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
        f"<b>✅ Фильтры сброшены</b>\n\n"
        f"<b>Поиск:</b> {data.get('query')}",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )
    await callback.answer("✅ Фильтры сброшены")


# ==================== ВЫПОЛНЕНИЕ ПОИСКА ====================

@router.callback_query(F.data == "search_now")
async def execute_search(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if not data.get("query"):
        await callback.answer("❌ Запрос не указан", show_alert=True)
        return

    await _safe_edit_text(callback.message, "🔍 Ищу вакансии...")

    per_page = int(data.get("per_page") or Config.VACANCIES_PER_PAGE)
    search_data = {k: v for k, v in data.items() if k in ("query", "city", "experience", "schedule", "salary", "only_with_salary", "exclude_words")}

    try:
        vacancies, total = await hh.search_vacancies(
            text=search_data.get("query"),
            area=search_data.get("city"),
            experience=search_data.get("experience"),
            schedule=search_data.get("schedule"),
            salary=search_data.get("salary"),
            only_with_salary=search_data.get("only_with_salary", False),
            exclude_words=search_data.get("exclude_words", []),
            page=0,
            per_page=per_page,
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        await _safe_edit_text(
            callback.message,
            "❌ Ошибка при поиске. Попробуйте позже.",
            reply_markup=kb.filters_kb(data),
        )
        await callback.answer("❌ Ошибка при поиске", show_alert=True)
        return

    if not vacancies:
        await _safe_edit_text(
            callback.message,
            "❌ Вакансии не найдены. Попробуйте изменить фильтры.",
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
    is_authorized = bool(user and getattr(user, "hh_access_token", None))

    first = _vacancy_from_short_dict(cache_vacancies[0])
    await _show_vacancy(
        callback.message,
        first,
        index=0,
        total=int(total or 0),
        user_id=callback.from_user.id,
        is_authorized=is_authorized,
    )
    await callback.answer()


# Продолжение в следующей части...

# ==================== НАВИГАЦИЯ ПО РЕЗУЛЬТАТАМ ====================

@router.callback_query(SearchStates.viewing_results, F.data.startswith("page_"))
async def change_page(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if callback.data == "page_info":
        total = int(data.get("total") or 0)
        current_index = int(data.get("current_index") or 0)

        if total == 0:
            await callback.answer("❌ Нет результатов", show_alert=True)
            return

        await callback.answer(
            f"Вакансия {current_index + 1} из {total:,}".replace(",", " "),
            show_alert=True,
        )
        return

    try:
        index = int(callback.data.replace("page_", "", 1))
    except ValueError:
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    total = int(data.get("total") or 0)

    if total and (index < 0 or index >= total):
        await callback.answer("❌ Страница не существует")
        return

    await _safe_edit_text(callback.message, "⏳ Загрузка...")

    vacancy, total2 = await _get_vacancy_at_index(state, index)
    if not vacancy:
        await callback.answer("❌ Вакансия не найдена")
        return

    await state.update_data(current_index=index, total=total2)

    user = await db.get_user(callback.from_user.id)
    is_authorized = bool(user and getattr(user, "hh_access_token", None))

    await _show_vacancy(callback.message, vacancy, index, total2, callback.from_user.id, is_authorized)
    await callback.answer()


# ==================== ДЕТАЛИ ВАКАНСИИ ====================

@router.callback_query(F.data.startswith("full_"))
async def show_full_vacancy(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.replace("full_", "", 1)

    await _safe_edit_text(callback.message, "⏳ Загружаю полное описание...")

    vacancy = await hh.get_vacancy_full(vacancy_id)
    if not vacancy:
        await callback.answer("❌ Вакансия не найдена", show_alert=True)
        return

    user = await db.get_user(callback.from_user.id)
    is_authorized = bool(user and getattr(user, "hh_access_token", None))
    is_applied = await db.was_applied(callback.from_user.id, vacancy_id)

    if isinstance(vacancy, dict):
        v = vacancy
        title = v.get("name") or ""
        url = v.get("alternate_url") or v.get("url") or ""
        employer = (v.get("employer") or {}).get("name") or ""
        area = (v.get("area") or {}).get("name") or ""
        experience = (v.get("experience") or {}).get("name") or ""
        schedule = (v.get("schedule") or {}).get("name") or ""
        employment = (v.get("employment") or {}).get("name") or ""
        salary = _format_salary_dict(v.get("salary"))
        desc = _hh_html_to_text(v.get("description"))

        text = f"<b>{title}</b>\n\n"
        text += f"<b>Компания:</b> {employer}\n"
        text += f"<b>Город:</b> {area}\n"
        text += f"<b>Зарплата:</b> {salary}\n"
        text += f"<b>Опыт:</b> {experience}\n"
        text += f"<b>График:</b> {schedule}\n"
        text += f"<b>Занятость:</b> {employment}\n\n"
        if url:
            text += f'<a href="{url}">🔗 Открыть на hh.ru</a>\n\n'
        if desc:
            text += f"<b>Описание:</b>\n{desc[:3000]}"
    else:
        title = getattr(vacancy, "name", None) or ""
        url = getattr(vacancy, "url", None) or ""
        employer = getattr(vacancy, "employer", None) or ""
        city = getattr(vacancy, "city", None) or ""
        experience = getattr(vacancy, "experience", None) or ""
        schedule = getattr(vacancy, "schedule", None) or ""
        salary = _format_salary_obj(vacancy)
        desc = _hh_html_to_text(getattr(vacancy, "description", None))
        requirement = _hh_html_to_text(getattr(vacancy, "requirement", None))

        text = f"<b>{title}</b>\n\n"
        text += f"<b>Компания:</b> {employer}\n"
        text += f"<b>Город:</b> {city}\n"
        text += f"<b>Зарплата:</b> {salary}\n"
        text += f"<b>Опыт:</b> {experience}\n"
        text += f"<b>График:</b> {schedule}\n\n"
        if url:
            text += f'<a href="{url}">🔗 Открыть на hh.ru</a>\n\n'
        if requirement:
            text += f"<b>Требования:</b>\n{requirement[:1500]}\n\n"
        if desc:
            text += f"<b>Описание:</b>\n{desc[:1500]}"

    if len(text) > 4000:
        text = text[:4000] + "\n\n<i>... описание сокращено</i>"

    await _safe_edit_text(
        callback.message,
        text,
        reply_markup=kb.vacancy_full_kb(vacancy_id, is_authorized, is_applied),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_list")
async def back_to_list(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_index = int(data.get("current_index") or 0)
    total = int(data.get("total") or 0)

    vacancy, total2 = await _get_vacancy_at_index(state, current_index)
    if not vacancy:
        await callback.answer("❌ Вакансия не найдена")
        return

    user = await db.get_user(callback.from_user.id)
    is_authorized = bool(user and getattr(user, "hh_access_token", None))

    await _show_vacancy(callback.message, vacancy, current_index, total2, callback.from_user.id, is_authorized)
    await callback.answer()


# ==================== ИЗБРАННОЕ ====================

async def _refresh_current_markup(callback: CallbackQuery, state: FSMContext, vacancy_id: str):
    data = await state.get_data()
    total = int(data.get("total") or 0)
    current_index = int(data.get("current_index") or 0)

    user = await db.get_user(callback.from_user.id)
    is_authorized = bool(user and getattr(user, "hh_access_token", None))

    is_fav = await db.is_favorite(callback.from_user.id, vacancy_id)
    is_applied = await db.was_applied(callback.from_user.id, vacancy_id)

    try:
        await callback.message.edit_reply_markup(
            reply_markup=kb.vacancy_kb(vacancy_id, is_fav, current_index, total, is_applied, is_authorized)
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("fav_"))
async def add_to_fav(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.replace("fav_", "", 1)

    data = await state.get_data()
    vacancy_data = None
    for v in data.get("cache_vacancies") or []:
        if v.get("id") == vacancy_id:
            vacancy_data = v
            break

    if not vacancy_data:
        vacancy_data = {"id": vacancy_id}

    success = await db.add_favorite(callback.from_user.id, vacancy_id, vacancy_data)
    if success:
        await callback.answer("⭐ Добавлено в избранное!")
        await _refresh_current_markup(callback, state, vacancy_id)
    else:
        await callback.answer("❌ Ошибка")


@router.callback_query(F.data.startswith("unfav_"))
async def remove_from_fav(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.replace("unfav_", "", 1)

    removed = await db.remove_favorite(callback.from_user.id, vacancy_id)
    if removed:
        await callback.answer("💔 Удалено из избранного")
    else:
        await callback.answer("❌ Ошибка")

    await _refresh_current_markup(callback, state, vacancy_id)


# ==================== ПОДПИСКИ ====================

@router.callback_query(F.data == "subscribe_current")
async def subscribe_from_search(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    count = await db.get_subscriptions_count(callback.from_user.id)
    if count >= Config.MAX_SUBSCRIPTIONS_PER_USER:
        await callback.answer(
            f"❌ Максимум {Config.MAX_SUBSCRIPTIONS_PER_USER} подписок",
            show_alert=True
        )
        return

    query = data.get("query")
    if not query:
        await callback.answer("❌ Запрос не найден", show_alert=True)
        return

    filters = {
        "city": data.get("city"),
        "city_name": data.get("city_name"),
        "experience": data.get("experience"),
        "schedule": data.get("schedule"),
        "salary": data.get("salary"),
        "only_with_salary": data.get("only_with_salary", False),
        "exclude_words": data.get("exclude_words", []),
    }

    sub_id = await db.add_subscription(
        user_id=callback.from_user.id,
        name=f"Подписка: {query[:50]}",
        query=query,
        filters=filters
    )

    if sub_id:
        await callback.answer(
            f"✅ Подписка создана на запрос \"{query}\"!",
            show_alert=True
        )
    else:
        await callback.answer("❌ Ошибка создания подписки", show_alert=True)


# ==================== ЗАКРЫТИЕ ====================

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
    try:
        await callback.message.delete()
    except:
        await callback.message.edit_text("❌ Отменено")
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=kb.main_menu_kb(callback.from_user.id)
        )
    await callback.answer()


# ==================== ИСТОРИЯ ПОИСКА ====================

@router.message(F.text == "🕐 История поиска")
async def show_search_history_menu(message: Message, state: FSMContext):
    await state.clear()

    history = await db.get_search_history(message.from_user.id, limit=10)

    text = "<b>🕐 История поиска</b>\n\n"
    text += "Ваши последние запросы:" if history else "История поиска пуста."

    await message.answer(
        text,
        reply_markup=kb.search_history_kb(history),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "history_empty")
async def history_empty(callback: CallbackQuery):
    await callback.answer("История поиска пуста", show_alert=True)


@router.callback_query(F.data == "clear_history")
async def clear_history(callback: CallbackQuery):
    await db.clear_search_history(callback.from_user.id)
    await callback.message.edit_text(
        "<b>🕐 История поиска</b>\n\n"
        "История очищена.",
        reply_markup=kb.search_history_kb([]),
        parse_mode="HTML",
    )
    await callback.answer("✅ История очищена")


@router.callback_query(F.data.startswith("repeat_search_"))
async def repeat_search_from_history(callback: CallbackQuery, state: FSMContext):
    idx_str = callback.data.replace("repeat_search_", "", 1)

    try:
        idx = int(idx_str)
    except ValueError:
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    history = await db.get_search_history(callback.from_user.id, limit=10)

    if idx < 0 or idx >= len(history):
        await callback.answer("❌ Запрос не найден", show_alert=True)
        return

    item = history[idx]
    query = (item.get("query") or "").strip()

    if not query:
        await callback.answer("❌ Пустой запрос", show_alert=True)
        return

    user_settings = await db.get_user_settings(callback.from_user.id)
    filters = item.get("filters") or {}

    await state.clear()
    await state.update_data(
        query=query,
        city=item.get("city") or user_settings.get("city_id"),
        city_name=item.get("city_name") or user_settings.get("city_name"),
        experience=filters.get("experience") or user_settings.get("experience"),
        schedule=filters.get("schedule") or user_settings.get("schedule"),
        salary=filters.get("salary") or user_settings.get("salary_from"),
        only_with_salary=filters.get("only_with_salary", user_settings.get("only_with_salary", False)),
        exclude_words=filters.get("exclude_words") or user_settings.get("exclude_words", []),
        current_index=0,
        total=0,
        per_page=Config.VACANCIES_PER_PAGE,
        cache_page=None,
        cache_vacancies=[],
        city_variants={},
    )

    await state.set_state(None)
    data = await state.get_data()

    await callback.message.edit_text(
        f"<b>Поиск:</b> {query}\n\n"
        "Настройте фильтры или начните поиск:",
        reply_markup=kb.filters_kb(data),
        parse_mode="HTML",
    )
    await callback.answer()


# ==================== FALLBACK ====================

@router.callback_query(SearchStates.viewing_results)
async def unknown_callback_in_results(callback: CallbackQuery):
    await callback.answer("Кнопка неактуальна или не поддерживается.", show_alert=False)


@router.message(SearchStates.viewing_results)
async def unknown_message_in_results(message: Message, state: FSMContext):
    await message.answer("Используйте кнопки навигации под вакансией или нажмите ❌ Закрыть.")
