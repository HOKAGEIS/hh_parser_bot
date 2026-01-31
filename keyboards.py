# keyboards.py (исправленный код)
from typing import List, Optional, Any, Dict, Union

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from config import Config


# ==================== УТИЛИТЫ ====================

def safe_callback(data: str, max_len: int = 64) -> str:
    """Обрезает callback_data до безопасной длины"""
    if len(data.encode('utf-8')) <= max_len:
        return data
    # Обрезаем с запасом для многобайтовых символов
    while len(data.encode('utf-8')) > max_len:
        data = data[:-1]
    return data


def get_user_field(user: Union[Dict, Any, None], field: str, default: Any = None) -> Any:
    """Универсальное получение поля из user (dict или object)"""
    if user is None:
        return default
    if isinstance(user, dict):
        return user.get(field, default)
    return getattr(user, field, default)


def back_kb(callback_data: str, text: str = "⬅️ Назад") -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой 'Назад'"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=text, callback_data=callback_data))
    return builder.as_markup()


def confirm_kb(confirm_data: str, cancel_data: str = "cancel") -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=confirm_data),
        InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_data),
    )
    return builder.as_markup()


# ==================== ГЛАВНОЕ МЕНЮ ====================

def main_menu_kb(user_id: int = None) -> ReplyKeyboardMarkup:
    """Главное меню бота"""
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

    # Кнопка админки только для администраторов
    if user_id and user_id in Config.ADMIN_IDS:
        builder.row(KeyboardButton(text="👑 Админ-панель"))

    return builder.as_markup(resize_keyboard=True)


# ==================== ФИЛЬТРЫ ПОИСКА ====================

def filters_kb(data: dict) -> InlineKeyboardMarkup:
    """Клавиатура фильтров поиска"""
    builder = InlineKeyboardBuilder()
    
    data = data or {}

    # Город
    city = data.get("city_name") or "Любой"
    builder.row(InlineKeyboardButton(
        text=f"📍 Город: {city[:20]}",
        callback_data="filter_city"
    ))

    # Зарплата
    salary = data.get("salary")
    if salary:
        salary_text = f"от {int(salary):,}₽".replace(",", " ")
    else:
        salary_text = "Любая"
    builder.row(InlineKeyboardButton(
        text=f"💰 Зарплата: {salary_text}",
        callback_data="filter_salary"
    ))

    # Опыт
    exp_id = data.get("experience")
    exp_name = Config.EXPERIENCE.get(exp_id, "Любой") if exp_id else "Любой"
    builder.row(InlineKeyboardButton(
        text=f"💼 Опыт: {exp_name}",
        callback_data="filter_experience"
    ))

    # График
    schedule_id = data.get("schedule")
    schedule_name = Config.SCHEDULE.get(schedule_id, "Любой") if schedule_id else "Любой"
    builder.row(InlineKeyboardButton(
        text=f"⏰ График: {schedule_name}",
        callback_data="filter_schedule"
    ))

    # Исключения
    exclude = data.get("exclude_words") or []
    exclude_text = f"({len(exclude)} слов)" if exclude else "Нет"
    builder.row(InlineKeyboardButton(
        text=f"🚫 Исключить: {exclude_text}",
        callback_data="filter_exclude"
    ))

    # Сброс
    builder.row(InlineKeyboardButton(
        text="🔄 Сбросить всё",
        callback_data="filter_reset"
    ))

    # Поиск и отмена
    builder.row(
        InlineKeyboardButton(text="🔍 Искать", callback_data="search_now"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
    )

    return builder.as_markup()


# ==================== ГОРОД (для поиска) ====================

def cities_kb() -> InlineKeyboardMarkup:
    """Выбор города для фильтров поиска"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="🌍 Любой город",
        callback_data="set_city_any"
    ))
    builder.row(InlineKeyboardButton(
        text="📍 Отправить геолокацию",
        callback_data="request_location"
    ))
    builder.row(InlineKeyboardButton(
        text="✏️ Ввести вручную",
        callback_data="enter_city_manual"
    ))

    # Популярные города (callback: set_city_{id})
    for city_id, city_name in list(Config.POPULAR_CITIES.items())[:6]:
        builder.row(InlineKeyboardButton(
            text=f"📍 {city_name}",
            callback_data=f"set_city_{city_id}"
        ))

    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back_to_filters"
    ))
    return builder.as_markup()


def found_cities_kb(cities: List[dict]) -> InlineKeyboardMarkup:
    """Список найденных городов из API (для поиска)"""
    builder = InlineKeyboardBuilder()

    for c in cities[:25]:
        city_id = str(c.get("id", ""))
        name = c.get("text") or c.get("name") or "Город"
        name_display = name[:60]
        builder.row(InlineKeyboardButton(
            text=f"📍 {name_display}",
            callback_data=f"set_city_{city_id}"
        ))

    builder.row(InlineKeyboardButton(
        text="🌍 Любой город",
        callback_data="set_city_any"
    ))
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="filter_city"
    ))
    return builder.as_markup()


def location_request_kb() -> ReplyKeyboardMarkup:
    """Клавиатура запроса геолокации"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(
        text="📍 Отправить местоположение",
        request_location=True
    ))
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


# ==================== ГОРОД (для настроек) ====================

def settings_cities_kb() -> InlineKeyboardMarkup:
    """Выбор города для настроек (отдельные callback_data)"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="🌍 Любой город",
        callback_data="settings_city_any"
    ))
    builder.row(InlineKeyboardButton(
        text="✏️ Ввести вручную",
        callback_data="settings_enter_city_manual"
    ))

    # Популярные города
    # Формат: settings_city_id:{id}:{name} (name обрезается для лимита 64 байта)
    for city_id, city_name in list(Config.POPULAR_CITIES.items())[:10]:
        # Ограничиваем имя города, чтобы уложиться в 64 байта
        callback = safe_callback(f"settings_city_id:{city_id}:{city_name}", 64)
        builder.row(InlineKeyboardButton(
            text=f"📍 {city_name}",
            callback_data=callback
        ))

    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back_to_settings"
    ))
    return builder.as_markup()


def settings_found_cities_kb(cities: List[dict]) -> InlineKeyboardMarkup:
    """Список найденных городов для настроек"""
    builder = InlineKeyboardBuilder()

    for c in cities[:20]:
        city_id = str(c.get("id", ""))
        name = c.get("text") or c.get("name") or "Город"
        # Безопасный callback с обрезкой имени
        callback = safe_callback(f"settings_city_id:{city_id}:{name}", 64)
        builder.row(InlineKeyboardButton(
            text=f"📍 {name[:50]}",
            callback_data=callback
        ))

    builder.row(InlineKeyboardButton(
        text="🌍 Любой город",
        callback_data="settings_city_any"
    ))
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back_to_settings"
    ))
    return builder.as_markup()


# ==================== ОПЫТ / ГРАФИК ====================

def experience_kb() -> InlineKeyboardMarkup:
    """Выбор опыта работы"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(
        text="💼 Любой опыт",
        callback_data="set_exp_any"
    ))

    for exp_id, exp_name in Config.EXPERIENCE.items():
        builder.row(InlineKeyboardButton(
            text=f"💼 {exp_name}",
            callback_data=f"set_exp_{exp_id}"
        ))

    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back_to_filters"
    ))
    return builder.as_markup()


def schedule_kb() -> InlineKeyboardMarkup:
    """Выбор графика работы"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(
        text="⏰ Любой график",
        callback_data="set_schedule_any"
    ))

    for sch_id, sch_name in Config.SCHEDULE.items():
        builder.row(InlineKeyboardButton(
            text=f"⏰ {sch_name}",
            callback_data=f"set_schedule_{sch_id}"
        ))

    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back_to_filters"
    ))
    return builder.as_markup()


# ==================== ЗАРПЛАТА ====================

def salary_kb() -> InlineKeyboardMarkup:
    """Выбор минимальной зарплаты"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="💰 Любая",
        callback_data="set_salary_any"
    ))
    builder.row(InlineKeyboardButton(
        text="✏️ Ввести сумму",
        callback_data="enter_salary_manual"
    ))

    salaries = [30000, 50000, 80000, 100000, 150000, 200000, 300000]
    for s in salaries:
        text = f"от {s:,}₽".replace(",", " ")
        builder.row(InlineKeyboardButton(
            text=text,
            callback_data=f"set_salary_{s}"
        ))

    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back_to_filters"
    ))
    return builder.as_markup()


# ==================== СЛОВА-ИСКЛЮЧЕНИЯ (для поиска) ====================

def exclude_words_kb(words: List[str]) -> InlineKeyboardMarkup:
    """Управление словами-исключениями в фильтрах поиска"""
    builder = InlineKeyboardBuilder()
    
    words = words or []

    builder.row(InlineKeyboardButton(
        text="➕ Добавить слово",
        callback_data="add_exclude_word"
    ))

    # Удаление по индексу (слово может быть длинным)
    for i, word in enumerate(words[:15]):
        shown = (word or "")[:40]
        builder.row(InlineKeyboardButton(
            text=f"❌ {shown}",
            callback_data=f"remove_exclude_{i}"
        ))

    if words:
        builder.row(InlineKeyboardButton(
            text="🗑 Очистить всё",
            callback_data="clear_exclude_words"
        ))

    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back_to_filters"
    ))
    return builder.as_markup()


# ==================== ИСТОРИЯ ПОИСКА ====================

def search_history_kb(history: List[dict]) -> InlineKeyboardMarkup:
    """Клавиатура истории поиска"""
    builder = InlineKeyboardBuilder()
    
    history = history or []

    if not history:
        builder.row(InlineKeyboardButton(
            text="📭 История пуста",
            callback_data="history_empty"
        ))
    else:
        for i, item in enumerate(history[:10]):
            query = (item.get("query") or "")[:25]
            city = item.get("city_name") or ""
            
            text = f"🔍 {query}"
            if city:
                text += f" ({city[:15]})"
            
            builder.row(InlineKeyboardButton(
                text=text[:50],
                callback_data=f"repeat_search_{i}"
            ))

        builder.row(InlineKeyboardButton(
            text="🗑 Очистить историю",
            callback_data="clear_history"
        ))

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
    Клавиатура для отображения вакансии.
    
    Args:
        vacancy_id: ID вакансии
        is_fav: В избранном или нет
        current_index: Текущий индекс (0-based)
        total: Общее количество вакансий
        is_applied: Уже откликнулся
        is_authorized: Авторизован на HH
    """
    builder = InlineKeyboardBuilder()

    # Подробнее
    builder.row(InlineKeyboardButton(
        text="📄 Подробнее",
        callback_data=f"full_{vacancy_id}"
    ))

    # Избранное
    if is_fav:
        builder.row(InlineKeyboardButton(
            text="💔 Убрать из избранного",
            callback_data=f"unfav_{vacancy_id}"
        ))
    else:
        builder.row(InlineKeyboardButton(
            text="⭐ В избранное",
            callback_data=f"fav_{vacancy_id}"
        ))

    # Навигация
    total = max(int(total or 0), 0)
    current_index = max(0, min(current_index, total - 1)) if total > 0 else 0
    
    nav: List[InlineKeyboardButton] = []

    if total <= 1:
        nav.append(InlineKeyboardButton(
            text="1/1",
            callback_data="page_info"
        ))
    else:
        # Кнопка "Назад"
        if current_index > 0:
            nav.append(InlineKeyboardButton(
                text="⬅️",
                callback_data=f"page_{current_index - 1}"
            ))
        
        # Счётчик
        nav.append(InlineKeyboardButton(
            text=f"{current_index + 1}/{total}",
            callback_data="page_info"
        ))
        
        # Кнопка "Вперёд"
        if current_index < total - 1:
            nav.append(InlineKeyboardButton(
                text="➡️",
                callback_data=f"page_{current_index + 1}"
            ))

    builder.row(*nav)

    # Подписка и закрытие
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
    """Клавиатура для полного описания вакансии"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад к списку",
        callback_data="back_to_list"
    ))
    builder.row(
        InlineKeyboardButton(text="🔔 Подписаться", callback_data="subscribe_current"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_search"),
    )
    return builder.as_markup()


# ==================== ИЗБРАННОЕ ====================

def favorites_list_kb(favorites: List[dict]) -> InlineKeyboardMarkup:
    """Список избранных вакансий"""
    builder = InlineKeyboardBuilder()
    
    favorites = favorites or []

    if not favorites:
        builder.row(InlineKeyboardButton(
            text="📭 Избранное пусто",
            callback_data="favorites_empty"
        ))
    else:
        for fav in favorites[:15]:
            vacancy_data = fav.get("vacancy_data") or {}
            name = (vacancy_data.get("name") or "Вакансия")[:30]
            vacancy_id = fav.get("vacancy_id", "")
            
            builder.row(InlineKeyboardButton(
                text=f"📌 {name}",
                callback_data=f"show_fav_{vacancy_id}"
            ))

        builder.row(InlineKeyboardButton(
            text="🗑 Очистить всё",
            callback_data="clear_favorites"
        ))

    return builder.as_markup()


def favorite_item_kb(vacancy_id: str) -> InlineKeyboardMarkup:
    """Действия с избранной вакансией"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(
        text="💔 Удалить из избранного",
        callback_data=f"del_fav_{vacancy_id}"
    ))
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back_to_favorites"
    ))
    return builder.as_markup()


# ==================== ПОДПИСКИ ====================

def subscriptions_list_kb(subs: List[Any]) -> InlineKeyboardMarkup:
    """Список подписок пользователя"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="➕ Новая подписка",
        callback_data="new_subscription"
    ))
    
    subs = subs or []

    for sub in subs[:10]:
        # Поддержка dict и object
        if isinstance(sub, dict):
            is_active = sub.get('active', False)
            query = sub.get('query', '')[:25]
            sub_id = sub.get('id', 0)
        else:
            is_active = getattr(sub, 'active', False)
            query = getattr(sub, 'query', '')[:25]
            sub_id = getattr(sub, 'id', 0)
        
        status = "🟢" if is_active else "🔴"
        builder.row(InlineKeyboardButton(
            text=f"{status} {query}",
            callback_data=f"sub_{sub_id}"
        ))

    return builder.as_markup()


def subscription_item_kb(sub_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Действия с подпиской"""
    builder = InlineKeyboardBuilder()

    if is_active:
        builder.row(InlineKeyboardButton(
            text="⏸ Приостановить",
            callback_data=f"pause_sub_{sub_id}"
        ))
    else:
        builder.row(InlineKeyboardButton(
            text="▶️ Возобновить",
            callback_data=f"resume_sub_{sub_id}"
        ))

    builder.row(InlineKeyboardButton(
        text="🗑 Удалить подписку",
        callback_data=f"delete_sub_{sub_id}"
    ))
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back_to_subs"
    ))

    return builder.as_markup()


# ==================== НАСТРОЙКИ ====================

def settings_kb(user: Union[Dict, Any, None]) -> InlineKeyboardMarkup:
    """Главное меню настроек"""
    builder = InlineKeyboardBuilder()

    # Город
    city_name = get_user_field(user, 'city_name') or get_user_field(user, 'default_city_name')
    city_display = (city_name or "Не выбран")[:20]
    builder.row(InlineKeyboardButton(
        text=f"📍 Город: {city_display}",
        callback_data="settings_city"
    ))

    # Только с зарплатой
    only_salary = get_user_field(user, 'only_with_salary', False)
    salary_status = "✅" if only_salary else "❌"
    builder.row(InlineKeyboardButton(
        text=f"💰 Только с зарплатой: {salary_status}",
        callback_data="settings_salary_toggle"
    ))

    # Слова-исключения
    exclude_words = get_user_field(user, 'exclude_words') or []
    exclude_count = len(exclude_words)
    builder.row(InlineKeyboardButton(
        text=f"🚫 Слова-исключения ({exclude_count})",
        callback_data="settings_exclude"
    ))

    # Уведомления
    builder.row(InlineKeyboardButton(
        text="🔔 Автоуведомления",
        callback_data="settings_notifications"
    ))

    # Сброс
    builder.row(InlineKeyboardButton(
        text="🔄 Сбросить настройки",
        callback_data="settings_reset"
    ))

    return builder.as_markup()


def settings_exclude_kb(words: List[str]) -> InlineKeyboardMarkup:
    """Управление словами-исключениями в настройках"""
    builder = InlineKeyboardBuilder()
    
    words = words or []

    builder.row(InlineKeyboardButton(
        text="➕ Добавить слово",
        callback_data="settings_add_exclude"
    ))

    # Удаление по индексу
    for i, word in enumerate(words[:10]):
        shown = (word or "")[:40]
        builder.row(InlineKeyboardButton(
            text=f"❌ {shown}",
            callback_data=f"settings_remove_exclude_{i}"
        ))

    if words:
        builder.row(InlineKeyboardButton(
            text="🗑 Очистить всё",
            callback_data="settings_clear_exclude"
        ))

    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back_to_settings"
    ))
    return builder.as_markup()


def notifications_kb(enabled: bool) -> InlineKeyboardMarkup:
    """Настройки уведомлений"""
    builder = InlineKeyboardBuilder()

    status = "✅ Включены" if enabled else "❌ Выключены"
    builder.row(InlineKeyboardButton(
        text=f"🔔 Уведомления: {status}",
        callback_data="toggle_notifications"
    ))
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back_to_settings"
    ))

    return builder.as_markup()


# ==================== ПОДДЕРЖКА ====================

def support_menu_kb() -> InlineKeyboardMarkup:
    """Меню поддержки"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="✏️ Написать обращение",
        callback_data="create_ticket"
    ))
    return builder.as_markup()


def support_ticket_kb(ticket_id: int) -> InlineKeyboardMarkup:
    """Действия с тикетом поддержки"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="✏️ Написать ещё",
        callback_data=f"continue_ticket_{ticket_id}"
    ))
    builder.row(InlineKeyboardButton(
        text="✅ Закрыть обращение",
        callback_data=f"close_my_ticket_{ticket_id}"
    ))
    return builder.as_markup()


# ==================== АДМИНКА ====================

def admin_kb() -> InlineKeyboardMarkup:
    """Главное меню админки"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="📊 Статистика",
        callback_data="admin_stats"
    ))
    builder.row(InlineKeyboardButton(
        text="📬 Обращения",
        callback_data="admin_tickets"
    ))
    builder.row(InlineKeyboardButton(
        text="📢 Рассылка",
        callback_data="admin_broadcast"
    ))
    builder.row(InlineKeyboardButton(
        text="👥 Пользователи",
        callback_data="admin_users"
    ))
    return builder.as_markup()


def admin_tickets_list_kb(tickets: List[dict]) -> InlineKeyboardMarkup:
    """Список тикетов для админа"""
    builder = InlineKeyboardBuilder()
    
    tickets = tickets or []

    if not tickets:
        builder.row(InlineKeyboardButton(
            text="📭 Нет обращений",
            callback_data="admin_no_tickets"
        ))
    else:
        for t in tickets[:10]:
            username = t.get("username") or str(t.get("user_id", "?"))
            ticket_id = t.get("id", 0)
            builder.row(InlineKeyboardButton(
                text=f"#{ticket_id} — @{username}"[:40],
                callback_data=f"admin_view_ticket_{ticket_id}"
            ))

    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="admin_back"
    ))
    return builder.as_markup()


def admin_ticket_kb(ticket_id: int) -> InlineKeyboardMarkup:
    """Действия админа с тикетом"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="✏️ Ответить",
        callback_data=f"admin_reply_{ticket_id}"
    ))
    builder.row(InlineKeyboardButton(
        text="✅ Закрыть тикет",
        callback_data=f"admin_close_ticket_{ticket_id}"
    ))
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="admin_tickets"
    ))
    return builder.as_markup()


def admin_back_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в админку"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="admin_back"
    ))
    return builder.as_markup()


def admin_broadcast_kb() -> InlineKeyboardMarkup:
    """Клавиатура для рассылки"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="📝 Создать рассылку",
        callback_data="admin_create_broadcast"
    ))
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="admin_back"
    ))
    return builder.as_markup()


def admin_confirm_broadcast_kb() -> InlineKeyboardMarkup:
    """Подтверждение рассылки"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Отправить", callback_data="admin_send_broadcast"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back"),
    )
    return builder.as_markup()
