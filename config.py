# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    HH_API_BASE_URL = os.getenv('HH_API_BASE_URL', 'https://api.hh.ru')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'vacancies.db')
    VACANCIES_PER_PAGE = 10  # Добавлен атрибут
    MAX_EXCLUDE_WORDS = 10    # Добавлен атрибут
    MAX_SUBSCRIPTIONS = 5     # Добавлен атрибут
    ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x]  # Добавлен атрибут

    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN must be set in environment variables")
