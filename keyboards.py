# keyboards.py (исправленный код)
from typing import List, Optional, Any, Dict

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from config import Config


# ==================== УТИЛИТЫ ====================

def back_kb(callback_data: str, text: str = "⬅️ Назад") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=text, callback_data=callback_data))
    return builder.as_markup()


# ==================== ГЛАВНОЕ МЕНЮ ====================

def main_menu_kb(user_id: int = None) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🔍 Поиск вакансий"),
        KeyboardButton(text="⭐ Избранное"),
    )
    builder.row(
        KeyboardButton(text="🔔 Подписки"),
        KeyboardButton(text="📊 Аналитика"),
    )
    builder.row(
        KeyboardButton(text="📨 Мои отклики"),
        KeyboardButton(text="✉️ Письма"),
    )
    builder.row(
        KeyboardButton(text="🕐 История поиска"),
        KeyboardButton(text="⚙️ Настройки"),
    )
    builder.row(KeyboardButton(text="💬 Поддержка"))

    if user_id and user_id in Config.ADMIN_IDS:
        builder.row(KeyboardButton(text="👑 Админ-панель"))

    return builder.as_markup(resize_keyboard=True)


# ==================== ФИЛЬТРЫ ПОИСКА (совместимо с search_router.py) ====================

def filters_kb(data: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Город
    city = data.get("city_name") or "Любой"
    builder.row(InlineKeyboardButton(text=f"📍 Город: {city}", callback_data="filter_city"))

    # Зарплата
    salary = data.get("salary")
    salary_text = f"от {salary:,}₽".replace(",", " ") if salary else "Любая"
    builder.row(InlineKeyboardButton(text=f"💰 Зарплата: {salary_text}", callback_data="filter_salary"))

    # Опыт
    exp = Config.EXPERIENCE.get(data.get("experience"), "Любой")
    builder.row(InlineKeyboardButton(text=f"💼 Опыт: {exp}", callback_data="filter_experience"))

    # График
    schedule = Config.SCHEDULE.get(data.get("schedule"), "Любой")
    builder.row(InlineKeyboardButton(text=f"⏰ График: {schedule}", callback_data="filter_schedule"))

    # Исключения
    exclude = data.get("exclude_words", []) or []
    exclude_text = f"({len(exclude)} слов)" if exclude else "Нет"
    builder.row(InlineKeyboardButton(text=f"🚫 Исключить: {exclude_text}", callback_data="filter_exclude"))

    # Сброс
    builder.row(InlineKeyboardButton(text="🔄 Сбросить всё", callback_data="filter_reset"))

    # Поиск и отмена
    builder.row(
        InlineKeyboardButton(text="🔍 Искать", callback_data="search_now"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
    )

    return builder.as_markup()


# ==================== ГОРОД ====================

def cities_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="🌍 Любой город", callback_data="set_city_any"))
    builder.row(InlineKeyboardButton(text="📍 Отправить геолокацию", callback_data="request_location"))
    builder.row(InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="enter_city_manual"))

    # ВАЖНО: callback_data только с id, без названия города
    for city_id, city_name in list(Config.POPULAR_CITIES.items())[:6]:
        builder.row(InlineKeyboardButton(text=f"📍 {city_name}", callback_data=f"set_city_{city_id}"))

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters"))
    return builder.as_markup()


def found_cities_kb(cities: List[dict]) -> InlineKeyboardMarkup:
    """
    Список найденных городов из API.
    ВАЖНО: callback_data только set_city_{id}, без текста.
    """
    builder = InlineKeyboardBuilder()

    for c in cities[:25]:
        city_id = str(c.get("id"))
        name = c.get("text") or c.get("name") or "Город"
        name = name[:60]
        builder.row(InlineKeyboardButton(text=f"📍 {name}", callback_data=f"set_city_{city_id}"))

    builder.row(InlineKeyboardButton(text="🌍 Любой город", callback_data="set_city_any"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="filter_city"))
    return builder.as_markup()


def location_request_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📍 Отправить местоположение", request_location=True))
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


# ==================== ОПЫТ / ГРАФИК ====================

def experience_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💼 Любой опыт", callback_data="set_exp_any"))

    for exp_id, exp_name in Config.EXPERIENCE.items():
        builder.row(InlineKeyboardButton(text=f"💼 {exp_name}", callback_data=f"set_exp_{exp_id}"))

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters"))
    return builder.as_markup()


def schedule_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⏰ Любой график", callback_data="set_schedule_any"))

    for sch_id, sch_name in Config.SCHEDULE.items():
        builder.row(InlineKeyboardButton(text=f"⏰ {sch_name}", callback_data=f"set_schedule_{sch_id}"))

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters"))
    return builder.as_markup()


# ==================== ЗАРПЛАТА ====================

def salary_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="💰 Любая", callback_data="set_salary_any"))
    builder.row(InlineKeyboardButton(text="✏️ Ввести сумму", callback_data="enter_salary_manual"))

    salaries = ["30000", "50000", "80000", "100000", "150000", "200000", "300000"]
    for s in salaries:
        text = f"от {int(s):,}₽".replace(",", " ")
        builder.row(InlineKeyboardButton(text=text, callback_data=f"set_salary_{s}"))

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters"))
    return builder.as_markup()


# ==================== СЛОВА-ИСКЛЮЧЕНИЯ ====================

def exclude_words_kb(words: List[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="➕ Добавить слово", callback_data="add_exclude_word"))

    # ВАЖНО: удаление по индексу, а не по слову (слово может быть длинным -> >64 bytes)
    for i, word in enumerate((words or [])[:15]):
        shown = (word or "")[:50]
        builder.row(InlineKeyboardButton(text=f"❌ {shown}", callback_data=f"remove_exclude_{i}"))

    if words:
        builder.row(InlineKeyboardButton(text="🗑 Очистить всё", callback_data="clear_exclude_words"))

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters"))
    return builder.as_markup()


# ==================== ИСТОРИЯ ПОИСКА ====================

def search_history_kb(history: List[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if not history:
        builder.row(InlineKeyboardButton(text="ostringstream", callback_data="history_empty"))
    else:
        for i, item in enumerate(history[:10]):
            query = (item.get("query", "") or "")[:25]
            city = item.get("city_name", "") or ""
            text = f"🔍 {query}"
            if city:
                text += f" ({city})"
            builder.row(InlineKeyboardButton(text=text, callback_data=f"repeat_search_{i}"))

    if history:
        builder.row(InlineKeyboardButton(text="🗑 Очистить историю", callback_data="clear_history"))

    return builder.as_markup()


# ==================== ВАКАНСИИ ====================

def vacancy_kb(
    vacancy_id: str,
    is_fav: bool,
    current_index: int,
    total: int,
    is_applied: bool = False,
    is_authorized: bool = False,
) -> InlineKeyboardMarkup:
    """
    В исправленном search_router:
    - current_index = глобальный индекс вакансии (0..total-1)
    - total = общее число вакансий
    """
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="📄 Подробнее", callback_data=f"full_{vacancy_id}"))

    if is_fav:
        builder.row(InlineKeyboardButton(text="💔 Убрать из избранного", callback_data=f"unfav_{vacancy_id}"))
    else:
        builder.row(InlineKeyboardButton(text="⭐ В избранное", callback_data=f"fav_{vacancy_id}"))

    # Навигация (по индексам)
    total = max(int(total or 0), 0)
    nav: List[InlineKeyboardButton] = []

    if total <= 0:
        nav.append(InlineKeyboardButton(text="1/1", callback_data="page_info"))
    else:
        if current_index > 0:
            nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"page_{current_index - 1}"))
        nav.append(InlineKeyboardButton(text=f"{current_index + 1}/{total}", callback_data="page_info"))
        if current_index < total - 1:
            nav.append(InlineKeyboardButton(text="➡️", callback_data=f"page_{current_index + 1}"))

    builder.row(*nav)

    builder.row(
        InlineKeyboardButton(text="🔔 Подписаться", callback_data="subscribe_current"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_search"),
    )

    return builder.as_markup()


def vacancy_full_kb(
    vacancy_id: str,
    is_authorized: bool = False,
    is_applied: bool = False,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_list"))
    builder.row(
        InlineKeyboardButton(text="🔔 Подписаться", callback_data="subscribe_current"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_search"),
    )
    return builder.as_markup()


# ==================== ИЗБРАННОЕ ====================

def favorites_list_kb(favorites: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for fav in favorites[:15]:
        name = (fav.get("vacancy_data", {}).get("name", "Вакансия"))[:30]
        builder.row(InlineKeyboardButton(text=f"📌 {name}", callback_data=f"show_fav_{fav.get('vacancy_id')}"))

    if favorites:
        builder.row(InlineKeyboardButton(text="🗑 Очистить", callback_data="clear_favorites"))

    return builder.as_markup()


def favorite_item_kb(vacancy_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💔 Удалить", callback_data=f"del_fav_{vacancy_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_favorites"))
    return builder.as_markup()


# ==================== ПОДПИСКИ ====================

def subscriptions_list_kb(subs: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="➕ Новая подписка", callback_data="new_subscription"))

    for sub in subs[:10]:
        status = "🟢" if getattr(sub, 'active', False) else "🔴"
        builder.row(InlineKeyboardButton(text=f"{status} {getattr(sub, 'query', '')[:25]}", callback_data=f"sub_{getattr(sub, 'id', 0)}"))

    return builder.as_markup()


def subscription_item_kb(sub_id: int, is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if is_active:
        builder.row(InlineKeyboardButton(text="⏸ Приостановить", callback_data=f"pause_sub_{sub_id}"))
    else:
        builder.row(InlineKeyboardButton(text="▶️ Возобновить", callback_data=f"resume_sub_{sub_id}"))

    builder.row(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_sub_{sub_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_subs"))

    return builder.as_markup()


# ==================== НАСТРОЙКИ ====================

def settings_kb(user) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    city = user.get('city_name', 'Не выбран') if isinstance(user, dict) else (getattr(user, 'default_city_name', 'Не выбран') if user and hasattr(user, 'default_city_name') else 'Не выбран')
    builder.row(InlineKeyboardButton(text=f"📍 Город: {city}", callback_data="settings_city"))

    salary_status = "✅" if (isinstance(user, dict) and user.get('only_with_salary')) or (hasattr(user, 'only_with_salary') and getattr(user, 'only_with_salary', False)) else "❌"
    builder.row(InlineKeyboardButton(text=f"💰 Только с зарплатой: {salary_status}", callback_data="settings_salary_toggle"))

    exclude_count = len(user.get('exclude_words', [])) if isinstance(user, dict) else len(getattr(user, 'exclude_words', [])) if hasattr(user, 'exclude_words') else 0
    builder.row(InlineKeyboardButton(text=f"🚫 Слова-исключения ({exclude_count})", callback_data="settings_exclude"))

    builder.row(InlineKeyboardButton(text="🔔 Автоуведомления", callback_data="settings_notifications"))
    builder.row(InlineKeyboardButton(text="🔄 Сбросить настройки", callback_data="settings_reset"))

    return builder.as_markup()


def settings_exclude_kb(words: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="➕ Добавить", callback_data="settings_add_exclude"))

    # ВАЖНО: удаление по индексу, а не по слову
    for i, word in enumerate((words or [])[:10]):
        shown = (word or "")[:50]
        builder.row(InlineKeyboardButton(text=f"❌ {shown}", callback_data=f"settings_remove_exclude_{i}"))

    if words:
        builder.row(InlineKeyboardButton(text="🗑 Очистить", callback_data="settings_clear_exclude"))

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_settings"))
    return builder.as_markup()


def notifications_kb(enabled: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    status = "✅ Включены" if enabled else "❌ Выключены"
    builder.row(InlineKeyboardButton(text=f"🔔 Уведомления: {status}", callback_data="toggle_notifications"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_settings"))

    return builder.as_markup()


# ==================== ПОДДЕРЖКА ====================

def support_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✏️ Написать обращение", callback_data="create_ticket"))
    return builder.as_markup()


def support_ticket_kb(ticket_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✏️ Написать ещё", callback_data=f"continue_ticket_{ticket_id}"))
    builder.row(InlineKeyboardButton(text="✅ Закрыть обращение", callback_data=f"close_my_ticket_{ticket_id}"))
    return builder.as_markup()


# ==================== АДМИНКА ====================

def admin_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))
    builder.row(InlineKeyboardButton(text="📬 Обращения", callback_data="admin_tickets"))
    builder.row(InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"))
    return builder.as_markup()


def admin_tickets_list_kb(tickets: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for t in tickets[:10]:
        username = t.get("username") or t.get("user_id")
        builder.row(
            InlineKeyboardButton(
                text=f"#{t['id']} — {username}",
                callback_data=f"admin_view_ticket_{t['id']}",
            )
        )

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back"))
    return builder.as_markup()


def admin_ticket_kb(ticket_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✏️ Ответить", callback_data=f"admin_reply_{ticket_id}"))
    builder.row(InlineKeyboardButton(text="✅ Закрыть", callback_data=f"admin_close_ticket_{ticket_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_tickets"))
    return builder.as_markup()


def admin_back_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back"))
    return builder.as_markup()
