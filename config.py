import os


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    HH_API_URL = "https://api.hh.ru"
    HH_USER_AGENT = "HH-Parser-Bot/1.0"
    
    VACANCIES_PER_PAGE = 20
    MAX_SUBSCRIPTIONS = 10
    MAX_EXCLUDE_WORDS = 20
    MAX_SEARCH_HISTORY = 10
    
    ADMIN_IDS = [8466698088]
    SUPPORT_USERNAME = "agress8r"
    
    MENU_BUTTONS = [
        "🔍 Поиск вакансий", "⭐ Избранное", "🔔 Подписки",
        "📊 Аналитика", "⚙️ Настройки", "💬 Поддержка",
        "📨 Мои отклики", "✉️ Письма", "👑 Админ-панель",
        "🕐 История поиска"
    ]
    
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
    
    EXPERIENCE = {
        "noExperience": "Нет опыта",
        "between1And3": "1-3 года",
        "between3And6": "3-6 лет",
        "moreThan6": "Более 6 лет",
    }
    
    SCHEDULE = {
        "fullDay": "Полный день",
        "shift": "Сменный график",
        "flexible": "Гибкий график",
        "remote": "Удалённая работа",
        "flyInFlyOut": "Вахта",
    }
    
    EMPLOYMENT = {
        "full": "Полная занятость",
        "part": "Частичная занятость",
        "project": "Проектная работа",
        "volunteer": "Волонтёрство",
        "probation": "Стажировка",
    }
    
    SEARCH_PERIOD = {
        "1": "За сутки",
        "3": "За 3 дня",
        "7": "За неделю",
        "30": "За месяц",
        "0": "За всё время",
    }
    
    SEARCH_FIELD = {
        "name": "В названии",
        "company_name": "В названии компании",
        "description": "В описании",
    }
    
    EDUCATION = {
        "not_required_or_not_specified": "Не требуется",
        "higher": "Высшее",
        "special_secondary": "Среднее специальное",
    }


config = Config()
