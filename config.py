import os
from dataclasses import dataclass, field
from typing import List

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8282068064:AAHZRE6qgaWdNO0j7_iTGzkNgWWIgXAx0S0")
    ADMIN_IDS: List[int] = field(default_factory=list)
    
    # HH.ru API
    HH_API_URL: str = "https://api.hh.ru"
    HH_USER_AGENT: str = "HH-Parser-Bot/1.0 (telegram-bot)"
    
    # OAuth HH.ru (для откликов)
    # Получить на https://dev.hh.ru/
    HH_CLIENT_ID: str = os.getenv("HH_CLIENT_ID", "")
    HH_CLIENT_SECRET: str = os.getenv("HH_CLIENT_SECRET", "")
    HH_REDIRECT_URI: str = os.getenv("HH_REDIRECT_URI", "https://your-domain.com/callback")
    
    # Лимиты
    VACANCIES_PER_PAGE: int = 20
    MAX_SUBSCRIPTIONS: int = 10
    MAX_EXCLUDE_WORDS: int = 30
    
    # Популярные города (для быстрого выбора)
    POPULAR_CITIES: dict = field(default_factory=lambda: {
        "1": "Москва",
        "2": "Санкт-Петербург",
        "3": "Екатеринбург",
        "4": "Новосибирск",
        "66": "Нижний Новгород",
        "88": "Казань",
        "104": "Краснодар",
        "68": "Самара",
        "72": "Уфа",
    })
    
    EXPERIENCE: dict = field(default_factory=lambda: {
        "noExperience": "Без опыта",
        "between1And3": "1-3 года",
        "between3And6": "3-6 лет",
        "moreThan6": "Более 6 лет",
    })
    
    SCHEDULE: dict = field(default_factory=lambda: {
        "remote": "Удалённая работа",
        "fullDay": "Полный день",
        "flexible": "Гибкий график",
        "shift": "Сменный график",
    })
    
    def __post_init__(self):
        admin_ids_str = os.getenv("ADMIN_IDS", "8466698088")
        if admin_ids_str:
            self.ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",")]

config = Config()

