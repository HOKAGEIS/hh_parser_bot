import os

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    HH_API_URL = "https://api.hh.ru"
    HH_USER_AGENT = "HH-Parser-Bot/1.0"
    
    VACANCIES_PER_PAGE = 20
    MAX_SUBSCRIPTIONS = 10
    MAX_EXCLUDE_WORDS = 20
    
    ADMIN_IDS = [8466698088]
    SUPPORT_USERNAME = "agress8r"  # Замени на свой username без @
    
    # Кнопки меню (для фильтрации)
    MENU_BUTTONS = [
        "🔍 Поиск вакансий",
        "⭐ Избранное",
        "🔔 Подписки",
        "📊 Аналитика",
        "⚙️ Настройки",
        "💬 Поддержка",
        "📨 Мои отклики",
        "✉️ Письма",
    ]
    
    POPULAR_CITIES = {
        "1": "Москва",
        "2": "Санкт-Петербург",
        "3": "Екатеринбург",
        "4": "Новосибирск",
        "88": "Казань",
        "66": "Нижний Новгород",
    }
    
    CITIES = POPULAR_CITIES
    
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


config = Config()
