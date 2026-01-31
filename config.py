import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('8282068064:AAHZRE6qgaWdNO0j7_iTGzkNgWWIgXAx0S0')
    HH_API_BASE_URL = os.getenv('HH_API_BASE_URL', 'https://api.hh.ru')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'vacancies.db')
    
    @classmethod
    def validate(cls):
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN must be set in environment variables")
        
        if len(cls.TELEGRAM_BOT_TOKEN) < 40:
            raise ValueError("Invalid TELEGRAM_BOT_TOKEN format")

