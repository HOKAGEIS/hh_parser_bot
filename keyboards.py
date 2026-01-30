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
        KeyboardButton(text="⚙️ Настройки")
    )
    return builder.as_markup(resize_keyboard=True)


# ==================== ПОИСК ====================

def search_options_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚀 Искать", callback_data="search_now"),
        InlineKeyboardButton(text="🎛 Фильтры", callback_data="search_filters")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def filters_kb(current_filters: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    city_text = config.CITIES.get(current_filters.get("city"), "Любой")
    exp_text = config.EXPERIENCE.get(current_filters.get("experience"), "Любой")
    schedule_text = config.SCHEDULE.get(current_filters.get("schedule"), "Любой")
    salary_text = f'от {current_filters.get("salary")}₽' if current_filters.get("salary") else "Любая"
    
    builder.row(
        InlineKeyboardButton(
            text=f"📍 Город: {city_text}",
            callback_data="filter_city"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"💼 Опыт: {exp_text}",
            callback_data="filter_experience"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"⏰ График: {schedule_text}",
            callback_data="filter_schedule"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"💰 Зарплата: {salary_text}",
            callback_data="filter_salary"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔄 Сбросить фильтры",
            callback_data="filter_reset"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Искать", callback_data="search_now"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_search")
    )
    
    return builder.as_markup()


def cities_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🌍 Любой город", callback_data="set_city_any")
    )
    
    for city_id, city_name in config.CITIES.items():
        builder.row(
            InlineKeyboardButton(
                text=f"📍 {city_name}",
                callback_data=f"set_city_{city_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters")
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
    
    salaries = [
        ("Любая", "any"),
        ("от 30 000 ₽", "30000"),
        ("от 50 000 ₽", "50000"),
        ("от 80 000 ₽", "80000"),
        ("от 100 000 ₽", "100000"),
        ("от 150 000 ₽", "150000"),
        ("от 200 000 ₽", "200000"),
    ]
    
    for text, value in salaries:
        builder.row(
            InlineKeyboardButton(
                text=f"💰 {text}",
                callback_data=f"set_salary_{value}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters")
    )
    
    return builder.as_markup()


# ==================== РЕЗУЛЬТАТЫ ПОИСКА ====================

def vacancy_kb(vacancy_id: str, is_favorite: bool, page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Избранное
    if is_favorite:
        builder.row(
            InlineKeyboardButton(
                text="💔 Удалить из избранного",
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
    
    # Подписка и закрыть
    builder.row(
        InlineKeyboardButton(text="🔔 Подписаться", callback_data="subscribe_current"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_search")
    )
    
    return builder.as_markup()


# ==================== ИЗБРАННОЕ ====================

def favorites_list_kb(favorites: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for fav in favorites[:10]:  # Максимум 10
        name = fav.vacancy_data.get("name", "Вакансия")[:30]
        builder.row(
            InlineKeyboardButton(
                text=f"📌 {name}",
                callback_data=f"show_fav_{fav.vacancy_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="🗑 Очистить всё", callback_data="clear_favorites")
    )
    
    return builder.as_markup()


def favorite_item_kb(vacancy_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💔 Удалить",
            callback_data=f"del_fav_{vacancy_id}"
        ),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_favorites")
    )
    return builder.as_markup()


# ==================== ПОДПИСКИ ====================

def subscriptions_list_kb(subscriptions: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for sub in subscriptions:
        status = "🟢" if sub.active else "🔴"
        query = sub.query[:25] + "..." if len(sub.query) > 25 else sub.query
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {query}",
                callback_data=f"sub_{sub.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="➕ Новая подписка", callback_data="new_subscription")
    )
    
    return builder.as_markup()


def subscription_item_kb(sub_id: int, is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    if is_active:
        builder.row(
            InlineKeyboardButton(text="⏸ Приостановить", callback_data=f"pause_sub_{sub_id}")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="▶️ Возобновить", callback_data=f"resume_sub_{sub_id}")
        )
    
    builder.row(
        InlineKeyboardButton(text="🔍 Проверить сейчас", callback_data=f"check_sub_{sub_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_sub_{sub_id}")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_subs")
    )
    
    return builder.as_markup()


# ==================== НАСТРОЙКИ ====================

def settings_kb(user) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    city_text = config.CITIES.get(user.default_city, "Не выбран") if user and user.default_city else "Не выбран"
    
    builder.row(
        InlineKeyboardButton(
            text=f"📍 Город по умолчанию: {city_text}",
            callback_data="settings_city"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"💰 Только с зарплатой: {'Да' if user and user.only_with_salary else 'Нет'}",
            callback_data="settings_salary_toggle"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑 Сбросить настройки",
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
