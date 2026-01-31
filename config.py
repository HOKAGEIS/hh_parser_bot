# config.py - полный файл
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    HH_API_BASE_URL = os.getenv('HH_API_BASE_URL', 'https://api.hh.ru')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'vacancies.db')
    
    # Добавьте админ ID если нужны
    ADMIN_IDS = [
        int(id.strip()) 
        for id in os.getenv('ADMIN_IDS', '').split(',') 
        if id.strip().isdigit()
    ]

    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN must be set in environment variables")

# СОЗДАЁМ ЭКЗЕМПЛЯР - ЭТО ВАЖНО!
config = Config()

# Валидация при импорте
Config.validate()
