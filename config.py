import os

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8282068064:AAHZRE6qgaWdNO0j7_iTGzkNgWWIgXAx0S0")
    
    HH_API_URL = "https://api.hh.ru"
    HH_USER_AGENT = "HH-Parser-Bot/1.0"
    
    VACANCIES_PER_PAGE = 30
    MAX_SUBSCRIPTIONS = 10
    MAX_EXCLUDE_WORDS = 20
    MAX_SEARCH_HISTORY = 20
    
    ADMIN_IDS = [8466698088]
    SUPPORT_USERNAME = "agress8r"
    
  MENU_BUTTONS = [
    "🔍 Поиск вакансий", "⭐ Избранное", "🔔 Подписки",
    "📊 Аналитика", "⚙️ Настройки", "💬 Поддержка",
    "📨 Мои отклики", "✉️ Письма", "👑 Админ-панель",
    "🕐 История поиска"
]
    
    # Города
    POPULAR_CITIES = {
        "1": "Москва",
        "2": "Санкт-Петербург",
        "3": "Екатеринбург",
        "4": "Новосибирск",
        "88": "Казань",
        "66": "Нижний Новгород",
        "54": "Красноярск",
        "68": "Омск",
        "72": "Самара",
        "99": "Уфа",
    }
    
    # Опыт работы
    EXPERIENCE = {
        "noExperience": "Нет опыта",
        "between1And3": "1-3 года",
        "between3And6": "3-6 лет",
        "moreThan6": "Более 6 лет",
    }
    
    # График работы
    SCHEDULE = {
        "fullDay": "Полный день",
        "shift": "Сменный график",
        "flexible": "Гибкий график",
        "remote": "Удалённая работа",
        "flyInFlyOut": "Вахта",
    }
    
    # Тип занятости
    EMPLOYMENT = {
        "full": "Полная занятость",
        "part": "Частичная занятость",
        "project": "Проектная работа",
        "volunteer": "Волонтёрство",
        "probation": "Стажировка",
    }
    
    # Период публикации
    SEARCH_PERIOD = {
        "1": "За сутки",
        "3": "За 3 дня",
        "7": "За неделю",
        "30": "За месяц",
        "0": "За всё время",
    }
    
    # Искать в
    SEARCH_FIELD = {
        "name": "В названии",
        "company_name": "В названии компании",
        "description": "В описании",
    }
    
    # Образование
    EDUCATION = {
        "not_required_or_not_specified": "Не требуется",
        "higher": "Высшее",
        "special_secondary": "Среднее специальное",
    }
    
    # Дополнительные фильтры
    LABELS = {
        "with_address": "С адресом",
        "accept_handicapped": "Для людей с инвалидностью",
        "accept_kids": "Доступно с 14 лет",
        "accredited_it_employer": "Аккредитованные IT компании",
        "low_responses": "Мало откликов",
    }


config = Config()

