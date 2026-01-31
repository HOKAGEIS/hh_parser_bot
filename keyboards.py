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

def main_menu_kb(user_id: int = None) -> ReplyKeyboardMarkup:
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
        KeyboardButton(text="🕐 История поиска"),
        KeyboardButton(text="⚙️ Настройки")
    )
    builder.row(
        KeyboardButton(text="💬 Поддержка")
    )
    
    if user_id and user_id in config.ADMIN_IDS:
        builder.row(KeyboardButton(text="👑 Админ-панель"))
    
    return builder.as_markup(resize_keyboard=True)


# ==================== ФИЛЬТРЫ ПОИСКА ====================

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
    exp = config.EXPERIENCE.get(data.get("experience"), "Любой")
    builder.row(InlineKeyboardButton(text=f"💼 Опыт: {exp}", callback_data="filter_experience"))
    
    # График
    schedule = config.SCHEDULE.get(data.get("schedule"), "Любой")
    builder.row(InlineKeyboardButton(text=f"⏰ График: {schedule}", callback_data="filter_schedule"))
    
    # Тип занятости
    employment = config.EMPLOYMENT.get(data.get("employment"), "Любой")
    builder.row(InlineKeyboardButton(text=f"📋 Занятость: {employment}", callback_data="filter_employment"))
    
    # Период публикации
    period = config.SEARCH_PERIOD.get(str(data.get("search_period", 0)), "За всё время")
    builder.row(InlineKeyboardButton(text=f"📅 Период: {period}", callback_data="filter_period"))
    
    # Расширенные фильтры
    builder.row(InlineKeyboardButton(text="🔧 Расширенные фильтры", callback_data="filter_advanced"))
    
    # Исключения
    exclude = data.get("exclude_words", [])
    exclude_text = f"({len(exclude)} слов)" if exclude else "Нет"
    builder.row(InlineKeyboardButton(text=f"🚫 Исключить: {exclude_text}", callback_data="filter_exclude"))
    
    # Сброс
    builder.row(InlineKeyboardButton(text="🔄 Сбросить всё", callback_data="filter_reset"))
    
    # Поиск и отмена
    builder.row(
        InlineKeyboardButton(text="🔍 Искать", callback_data="search_now"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    
    return builder.as_markup()


def advanced_filters_kb(data: dict) -> InlineKeyboardMarkup:
    """Расширенные фильтры"""
    builder = InlineKeyboardBuilder()
    
    # Искать в
    search_field = config.SEARCH_FIELD.get(data.get("search_field"), "Везде")
    builder.row(InlineKeyboardButton(text=f"🔎 Искать в: {search_field}", callback_data="filter_search_field"))
    
    # Образование
    education = config.EDUCATION.get(data.get("education"), "Любое")
    builder.row(InlineKeyboardButton(text=f"🎓 Образование: {education}", callback_data="filter_education"))
    
    # Чекбоксы
    checks = []
    
    # С адресом
    with_address = "✅" if data.get("with_address") else "❌"
    builder.row(InlineKeyboardButton(text=f"{with_address} С адресом", callback_data="toggle_with_address"))
    
    # Аккредитованные IT
    accredited = "✅" if data.get("accredited_it") else "❌"
    builder.row(InlineKeyboardButton(text=f"{accredited} Аккредитованные IT", callback_data="toggle_accredited_it"))
    
    # Без агентств
    no_agency = "✅" if data.get("exclude_agency") else "❌"
    builder.row(InlineKeyboardButton(text=f"{no_agency} Без кадровых агентств", callback_data="toggle_no_agency"))
    
    # Для людей с инвалидностью
    handicapped = "✅" if data.get("accept_handicapped") else "❌"
    builder.row(InlineKeyboardButton(text=f"{handicapped} Для людей с инвалидностью", callback_data="toggle_handicapped"))
    
    # Доступно с 14 лет
    kids = "✅" if data.get("accept_kids") else "❌"
    builder.row(InlineKeyboardButton(text=f"{kids} Доступно с 14 лет", callback_data="toggle_accept_kids"))
    
    # Стажировка
    internship = "✅" if data.get("internship") else "❌"
    builder.row(InlineKeyboardButton(text=f"{internship} Стажировка", callback_data="toggle_internship"))
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад к фильтрам", callback_data="back_to_filters"))
    
    return builder.as_markup()


def period_kb() -> InlineKeyboardMarkup:
    """Период публикации"""
    builder = InlineKeyboardBuilder()
    
    for period_id, period_name in config.SEARCH_PERIOD.items():
        builder.row(InlineKeyboardButton(text=f"📅 {period_name}", callback_data=f"set_period_{period_id}"))
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters"))
    return builder.as_markup()


def employment_kb() -> InlineKeyboardMarkup:
    """Тип занятости"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="📋 Любая", callback_data="set_employment_any"))
    
    for emp_id, emp_name in config.EMPLOYMENT.items():
        builder.row(InlineKeyboardButton(text=f"📋 {emp_name}", callback_data=f"set_employment_{emp_id}"))
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters"))
    return builder.as_markup()


def search_field_kb() -> InlineKeyboardMarkup:
    """Искать в"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="🔎 Везде", callback_data="set_search_field_any"))
    
    for field_id, field_name in config.SEARCH_FIELD.items():
        builder.row(InlineKeyboardButton(text=f"🔎 {field_name}", callback_data=f"set_search_field_{field_id}"))
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="filter_advanced"))
    return builder.as_markup()


def education_kb() -> InlineKeyboardMarkup:
    """Образование"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="🎓 Любое", callback_data="set_education_any"))
    
    for edu_id, edu_name in config.EDUCATION.items():
        builder.row(InlineKeyboardButton(text=f"🎓 {edu_name}", callback_data=f"set_education_{edu_id}"))
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="filter_advanced"))
    return builder.as_markup()


def cities_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="🌍 Любой город", callback_data="set_city_any"))
    builder.row(InlineKeyboardButton(text="📍 Определить автоматически", callback_data="detect_city"))
    builder.row(InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="enter_city_manual"))
    
    for city_id, city_name in list(config.POPULAR_CITIES.items())[:6]:
        builder.row(InlineKeyboardButton(text=f"📍 {city_name}", callback_data=f"set_city_{city_id}_{city_name}"))
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters"))
    return builder.as_markup()


def experience_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="💼 Любой опыт", callback_data="set_exp_any"))
    
    for exp_id, exp_name in config.EXPERIENCE.items():
        builder.row(InlineKeyboardButton(text=f"💼 {exp_name}", callback_data=f"set_exp_{exp_id}"))
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters"))
    return builder.as_markup()


def schedule_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="⏰ Любой график", callback_data="set_schedule_any"))
    
    for sch_id, sch_name in config.SCHEDULE.items():
        builder.row(InlineKeyboardButton(text=f"⏰ {sch_name}", callback_data=f"set_schedule_{sch_id}"))
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters"))
    return builder.as_markup()


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


def exclude_words_kb(words: List[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="➕ Добавить слово", callback_data="add_exclude_word"))
    
    for word in words[:15]:
        builder.row(InlineKeyboardButton(text=f"❌ {word}", callback_data=f"remove_exclude_{word}"))
    
    if words:
        builder.row(InlineKeyboardButton(text="🗑 Очистить всё", callback_data="clear_exclude_words"))
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters"))
    return builder.as_markup()


# ==================== ИСТОРИЯ ПОИСКА ====================

def search_history_kb(history: List[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    if not history:
        builder.row(InlineKeyboardButton(text="📭 История пуста", callback_data="history_empty"))
    else:
        for i, item in enumerate(history[:10]):
            query = item.get("query", "")[:25]
            city = item.get("city_name", "")
            text = f"🔍 {query}"
            if city:
                text += f" ({city})"
            builder.row(InlineKeyboardButton(text=text, callback_data=f"repeat_search_{i}"))
    
    if history:
        builder.row(InlineKeyboardButton(text="🗑 Очистить историю", callback_data="clear_history"))
    
    return builder.as_markup()


# ==================== ВАКАНСИИ ====================

def vacancy_kb(vacancy_id: str, is_fav: bool, page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="📄 Подробнее", callback_data=f"full_{vacancy_id}"))
    
    if is_fav:
        builder.row(InlineKeyboardButton(text="💔 Убрать из избранного", callback_data=f"unfav_{vacancy_id}"))
    else:
        builder.row(InlineKeyboardButton(text="⭐ В избранное", callback_data=f"fav_{vacancy_id}"))
    
    # Навигация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"page_{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="page_info"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"page_{page + 1}"))
    builder.row(*nav)
    
    builder.row(
        InlineKeyboardButton(text="🔔 Подписаться", callback_data="subscribe_current"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_search")
    )
    
    return builder.as_markup()


def vacancy_full_kb(vacancy_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_list"))
    return builder.as_markup()


# ==================== ИЗБРАННОЕ ====================

def favorites_list_kb(favorites: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for fav in favorites[:15]:
        name = fav.vacancy_data.get("name", "Вакансия")[:30]
        builder.row(InlineKeyboardButton(text=f"📌 {name}", callback_data=f"show_fav_{fav.vacancy_id}"))
    
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
        status = "🟢" if sub.active else "🔴"
        builder.row(InlineKeyboardButton(text=f"{status} {sub.query[:25]}", callback_data=f"sub_{sub.id}"))
    
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
    
    city = user.default_city_name if user and user.default_city_name else "Не выбран"
    builder.row(InlineKeyboardButton(text=f"📍 Город: {city}", callback_data="settings_city"))
    
    salary_status = "✅" if user and user.only_with_salary else "❌"
    builder.row(InlineKeyboardButton(text=f"💰 Только с зарплатой: {salary_status}", callback_data="settings_salary_toggle"))
    
    exclude_count = len(user.exclude_words) if user and user.exclude_words else 0
    builder.row(InlineKeyboardButton(text=f"🚫 Слова-исключения ({exclude_count})", callback_data="settings_exclude"))
    
    builder.row(InlineKeyboardButton(text="🔔 Автоуведомления", callback_data="settings_notifications"))
    builder.row(InlineKeyboardButton(text="🔄 Сбросить настройки", callback_data="settings_reset"))
    
    return builder.as_markup()


def settings_exclude_kb(words: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="➕ Добавить", callback_data="settings_add_exclude"))
    
    for word in words[:10]:
        builder.row(InlineKeyboardButton(text=f"❌ {word}", callback_data=f"settings_remove_exclude_{word}"))
    
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
        username = t['username'] or t['user_id']
        builder.row(InlineKeyboardButton(text=f"#{t['id']} — {username}", callback_data=f"admin_view_ticket_{t['id']}"))
    
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
