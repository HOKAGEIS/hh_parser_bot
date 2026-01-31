# config.py - полный файл с всеми необходимыми настройками
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Основные настройки
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    HH_API_BASE_URL = os.getenv('HH_API_BASE_URL', 'https://api.hh.ru')
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
        for id in os.getenv('ADMIN_IDS', '8466698088').split(',') 
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
