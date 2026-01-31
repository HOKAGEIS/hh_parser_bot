# config.py - исправленный файл
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Основные настройки
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    HH_API_BASE_URL = os.getenv('HH_API_BASE_URL', 'https://api.hh.ru ')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'vacancies.db')
    
    # Настройки пагинации
    VACANCIES_PER_PAGE = int(os.getenv('VACANCIES_PER_PAGE', '5'))
    MAX_PAGES = int(os.getenv('MAX_PAGES', '20'))
    
    # Настройки кэша
    CACHE_TTL = int(os.getenv('CACHE_TTL', '3600'))  # 1 час
    
    # Настройки поиска
    DEFAULT_SEARCH_PERIOD = int(os.getenv('DEFAULT_SEARCH_PERIOD', '30'))  # дней
    MAX_EXCLUDE_WORDS = int(os.getenv('MAX_EXCLUDE_WORDS', '10'))
    
    # Настройки подписок
    MAX_SUBSCRIPTIONS_PER_USER = int(os.getenv('MAX_SUBSCRIPTIONS_PER_USER', '5'))
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '3600'))  # секунд
    
    # Настройки избранного
    MAX_FAVORITES_PER_USER = int(os.getenv('MAX_FAVORITES_PER_USER', '50'))
    
    # ID администраторов
    ADMIN_IDS = [
        int(id.strip()) 
        for id in os.getenv('ADMIN_IDS', '').split(',') 
        if id.strip().isdigit()
    ]
    
    # Настройки уведомлений
    NOTIFICATION_HOUR = int(os.getenv('NOTIFICATION_HOUR', '10'))  # час для уведомлений
    
    # API ключи
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    
    # Лимиты API
    API_RATE_LIMIT = int(os.getenv('API_RATE_LIMIT', '10'))  # запросов в секунду
    
    # Настройки базы данных
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '10'))
    DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '20'))
    
    # Режим отладки
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Webhook настройки (если используете)
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
    WEBHOOK_PATH = os.getenv('WEBHOOK_PATH', '/webhook')
    WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', '8080'))
    
    # Кнопки главного меню
    MENU_BUTTONS = [
        "🔍 Поиск вакансий",
        "⭐ Избранное",
        "🔔 Подписки",
        "📊 Аналитика",
        "🕐 История поиска",
        "⚙️ Настройки",
        "💬 Поддержка",
        "👑 Админ-панель",
        "❌ Отмена",
        "⬅️ Назад"
    ]
    
    # Популярные города
    POPULAR_CITIES = {
        "1": "Москва",
        "2": "Санкт-Петербург",
        "3": "Новосибирск",
        "4": "Екатеринбург",
        "5": "Казань",
        "6": "Нижний Новгород",
        "7": "Челябинск",
        "8": "Самара",
        "9": "Омск",
        "10": "Ростов-на-Дону"
    }
    
    # Опыт работы
    EXPERIENCE = {
        "noExperience": "Нет опыта",
        "between1And3": "От 1 года до 3 лет",
        "between3And6": "От 3 до 6 лет",
        "moreThan6": "Более 6 лет"
    }
    
    # График работы
    SCHEDULE = {
        "fullDay": "Полный день",
        "shift": "Сменный график",
        "flexible": "Гибкий график",
        "remote": "Удаленная работа",
        "partTime": "Неполный рабочий день"
    }
    
    @classmethod
    def validate(cls):
        """Проверка обязательных настроек"""
        if not cls.BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN must be set in environment variables")
        
        # Проверяем корректность числовых значений
        if cls.VACANCIES_PER_PAGE < 1 or cls.VACANCIES_PER_PAGE > 20:
            cls.VACANCIES_PER_PAGE = 5
        
        if cls.MAX_PAGES < 1:
            cls.MAX_PAGES = 20
        
        return True

# Создаём экземпляр для обратной совместимости
config = Config()

# Валидация при импорте
Config.validate()

# Экспорт
__all__ = ['Config', 'config']
