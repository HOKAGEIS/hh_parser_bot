from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from config import config
from typing import List

# ==================== ГЛАВНОЕ МЕНЮ ====================

def main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🔍 Поиск вакансий"),
        KeyboardButton(text="⭐ Избранное")
    )
    builder.row(
        KeyboardButton(text="🔔 Подписки"),
        KeyboardButton(text="📊 Аналитика")
    )
    builder.row(
        KeyboardButton(text="📨 Мои отклики"),
        KeyboardButton(text="✉️ Письма")
    )
    builder.row(
        KeyboardButton(text="⚙️ Настройки")
    )
    return builder.as_markup(resize_keyboard=True)


# ==================== ФИЛЬТРЫ ====================

def filters_kb(current_filters: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Город
    city_name = current_filters.get("city_name") or "Любой"
    builder.row(
        InlineKeyboardButton(
            text=f"📍 Город: {city_name}",
            callback_data="filter_city"
        )
    )
    
    # Опыт
    exp_text = config.EXPERIENCE.get(current_filters.get("experience"), "Любой")
    builder.row(
        InlineKeyboardButton(
            text=f"💼 Опыт: {exp_text}",
            callback_data="filter_experience"
        )
    )
    
    # График
    schedule_text = config.SCHEDULE.get(current_filters.get("schedule"), "Любой")
    builder.row(
        InlineKeyboardButton(
            text=f"⏰ График: {schedule_text}",
            callback_data="filter_schedule"
        )
    )
    
    # Зарплата
    salary = current_filters.get("salary")
    salary_text = f"от {salary:,}₽".replace(",", " ") if salary else "Любая"
    builder.row(
        InlineKeyboardButton(
            text=f"💰 Зарплата: {salary_text}",
            callback_data="filter_salary"
        )
    )
    
    # Исключения
    exclude = current_filters.get("exclude_words", [])
    exclude_text = f"({len(exclude)} слов)" if exclude else "Нет"
    builder.row(
        InlineKeyboardButton(
            text=f"🚫 Исключить: {exclude_text}",
            callback_data="filter_exclude"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔄 Сбросить всё",
            callback_data="filter_reset"
        )
    )
    
    builder.row(
        InlineKeyboardButton(text="🔍 Искать", callback_data="search_now"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    
    return builder.as_markup()


def cities_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🌍 Любой город", callback_data="set_city_any")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="enter_city_manual")
    )
    
    # Популярные города
    for city_id, city_name in list(config.POPULAR_CITIES.items())[:6]:
        builder.row(
            InlineKeyboardButton(
                text=f"📍 {city_name}",
                callback_data=f"set_city_{city_id}_{city_name}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters")
    )
    
    return builder.as_markup()


def found_cities_kb(cities: List[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for city in cities[:8]:
        city_id = city.get("id")
        city_name = city.get("text", city.get("name", ""))
        builder.row(
            InlineKeyboardButton(
                text=f"📍 {city_name}",
                callback_data=f"set_city_{city_id}_{city_name[:20]}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="🔄 Ввести другой", callback_data="enter_city_manual"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="filter_city")
    )
    
    return builder.as_markup()


def experience_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📋 Любой опыт", callback_data="set_exp_any")
    )
    
    for exp_id, exp_name in config.EXPERIENCE.items():
        builder.row(
            InlineKeyboardButton(
                text=f"💼 {exp_name}",
                callback_data=f"set_exp_{exp_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters")
    )
    
    return builder.as_markup()


def schedule_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📋 Любой график", callback_data="set_schedule_any")
    )
    
    for schedule_id, schedule_name in config.SCHEDULE.items():
        builder.row(
            InlineKeyboardButton(
                text=f"⏰ {schedule_name}",
                callback_data=f"set_schedule_{schedule_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters")
    )
    
    return builder.as_markup()


def salary_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="💰 Любая", callback_data="set_salary_any")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Ввести свою сумму", callback_data="enter_salary_manual")
    )
    
    salaries = [
        ("от 30 000 ₽", "30000"),
        ("от 50 000 ₽", "50000"),
        ("от 80 000 ₽", "80000"),
        ("от 100 000 ₽", "100000"),
        ("от 150 000 ₽", "150000"),
        ("от 200 000 ₽", "200000"),
        ("от 300 000 ₽", "300000"),
    ]
    
    for text, value in salaries:
        builder.row(
            InlineKeyboardButton(text=text, callback_data=f"set_salary_{value}")
        )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters")
    )
    
    return builder.as_markup()


def exclude_words_kb(words: List[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="➕ Добавить слово", callback_data="add_exclude_word")
    )
    
    if words:
        for word in words[:15]:
            builder.row(
                InlineKeyboardButton(
                    text=f"❌ {word}",
                    callback_data=f"remove_exclude_{word}"
                )
            )
        
        builder.row(
            InlineKeyboardButton(text="🗑 Очистить всё", callback_data="clear_exclude_words")
        )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters")
    )
    
    return builder.as_markup()


# ==================== РЕЗУЛЬТАТЫ ====================

def vacancy_kb(
    vacancy_id: str, 
    is_favorite: bool, 
    page: int, 
    total_pages: int,
    is_applied: bool = False,
    is_authorized: bool = False
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Полное описание
    builder.row(
        InlineKeyboardButton(
            text="📄 Подробнее",
            callback_data=f"full_{vacancy_id}"
        )
    )
    
    # Избранное
    if is_favorite:
        builder.row(
            InlineKeyboardButton(
                text="💔 Убрать из избранного",
                callback_data=f"unfav_{vacancy_id}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="⭐ В избранное",
                callback_data=f"fav_{vacancy_id}"
            )
        )
    
    # Отклик
    if is_authorized:
        if is_applied:
            builder.row(
                InlineKeyboardButton(
                    text="✅ Отклик отправлен",
                    callback_data="already_applied"
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text="📨 Откликнуться",
                    callback_data=f"apply_{vacancy_id}"
                )
            )
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"page_{page - 1}")
        )
    
    nav_buttons.append(
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="page_info")
    )
    
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"page_{page + 1}")
        )
    
    builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(text="🔔 Подписаться", callback_data="subscribe_current"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_search")
    )
    
    return builder.as_markup()


def vacancy_full_kb(vacancy_id: str, is_authorized: bool = False, is_applied: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    if is_authorized and not is_applied:
        builder.row(
            InlineKeyboardButton(
                text="📨 Откликнуться",
                callback_data=f"apply_{vacancy_id}"
            )
        )
    elif is_applied:
        builder.row(
            InlineKeyboardButton(
                text="✅ Отклик отправлен",
                callback_data="already_applied"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="back_to_list")
    )
    
    return builder.as_markup()


# ==================== ОТКЛИКИ ====================

def apply_kb(vacancy_id: str, letters: List[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📨 Без сопроводительного",
            callback_data=f"apply_now_{vacancy_id}_none"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="✏️ Написать сейчас",
            callback_data=f"apply_write_{vacancy_id}"
        )
    )
    
    if letters:
        builder.row(
            InlineKeyboardButton(
                text="📝 Выбрать шаблон",
                callback_data=f"apply_template_{vacancy_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_list")
    )
    
    return builder.as_markup()


def letter_templates_kb(vacancy_id: str, letters: List[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for letter in letters[:10]:
        prefix = "⭐ " if letter["is_default"] else ""
        builder.row(
            InlineKeyboardButton(
                text=f"{prefix}{letter['name']}",
                callback_data=f"use_letter_{vacancy_id}_{letter['id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"apply_{vacancy_id}")
    )
    
    return builder.as_markup()


def resumes_kb(resumes: List[dict], vacancy_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for resume in resumes[:5]:
        title = resume.get("title", "Резюме")[:30]
        builder.row(
            InlineKeyboardButton(
                text=f"📄 {title}",
                callback_data=f"resume_{vacancy_id}_{resume['id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_list")
    )
    
    return builder.as_markup()


# ==================== СОПРОВОДИТЕЛЬНЫЕ ПИСЬМА ====================

def cover_letters_menu_kb(letters: List[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="➕ Создать шаблон", callback_data="create_letter")
    )
    
    for letter in letters[:10]:
        prefix = "⭐ " if letter["is_default"] else ""
        builder.row(
            InlineKeyboardButton(
                text=f"{prefix}{letter['name']}",
                callback_data=f"view_letter_{letter['id']}"
            )
        )
    
    return builder.as_markup()


def cover_letter_kb(letter_id: int, is_default: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    if not is_default:
        builder.row(
            InlineKeyboardButton(
                text="⭐ Сделать основным",
                callback_data=f"default_letter_{letter_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="✏️ Редактировать",
            callback_data=f"edit_letter_{letter_id}"
        ),
        InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data=f"delete_letter_{letter_id}"
        )
    )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_letters")
    )
    
    return builder.as_markup()


# ==================== НАСТРОЙКИ ====================

def settings_kb(user, is_authorized: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Город
    city_name = user.default_city_name if user and user.default_city_name else "Не выбран"
    builder.row(
        InlineKeyboardButton(
            text=f"📍 Город: {city_name}",
            callback_data="settings_city"
        )
    )
    
    # Только с зарплатой
    salary_status = "✅" if user and user.only_with_salary else "❌"
    builder.row(
        InlineKeyboardButton(
            text=f"💰 Только с зарплатой: {salary_status}",
            callback_data="settings_salary_toggle"
        )
    )
    
    # Исключения
    exclude_count = len(user.exclude_words) if user and user.exclude_words else 0
    builder.row(
        InlineKeyboardButton(
            text=f"🚫 Слова-исключения ({exclude_count})",
            callback_data="settings_exclude"
        )
    )
    
    # Авторизация HH
    if is_authorized:
        builder.row(
            InlineKeyboardButton(
                text="🔗 HH.ru: Подключено ✅",
                callback_data="hh_disconnect"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="🔗 Подключить HH.ru для откликов",
                callback_data="hh_connect"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="🔄 Сбросить настройки",
            callback_data="settings_reset"
        )
    )
    
    return builder.as_markup()


# ==================== ОБЩИЕ ====================

def confirm_kb(action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}"),
        InlineKeyboardButton(text="❌ Нет", callback_data="cancel")
    )
    return builder.as_markup()


def back_kb(callback_data: str = "cancel") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=callback_data)
    )
    return builder.as_markup()
