import aiohttp
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from config import config

@dataclass
class Vacancy:
    id: str
    name: str
    url: str
    employer: str
    employer_logo: Optional[str]
    salary_from: Optional[int]
    salary_to: Optional[int]
    salary_currency: Optional[str]
    city: str
    experience: str
    schedule: str
    requirement: Optional[str]
    responsibility: Optional[str]
    published_at: str
    
    @property
    def salary_text(self) -> str:
        if not self.salary_from and not self.salary_to:
            return "💰 Зарплата не указана"
        
        currency_symbols = {"RUR": "₽", "USD": "$", "EUR": "€", "KZT": "₸"}
        symbol = currency_symbols.get(self.salary_currency, self.salary_currency or "")
        
        if self.salary_from and self.salary_to:
            return f"💰 {self.salary_from:,} - {self.salary_to:,} {symbol}".replace(",", " ")
        elif self.salary_from:
            return f"💰 от {self.salary_from:,} {symbol}".replace(",", " ")
        else:
            return f"💰 до {self.salary_to:,} {symbol}".replace(",", " ")
    
    def to_message(self) -> str:
        # Очищаем текст от HTML тегов
        req = self.requirement or ""
        req = req.replace("<highlighttext>", "").replace("</highlighttext>", "")
        if len(req) > 200:
            req = req[:200] + "..."
        
        return (
            f"📌 <b>{self.name}</b>\n\n"
            f"🏢 {self.employer}\n"
            f"📍 {self.city}\n"
            f"{self.salary_text}\n"
            f"📋 Опыт: {self.experience}\n"
            f"⏰ {self.schedule}\n\n"
            f"📝 {req}\n\n"
            f"🔗 <a href='{self.url}'>Открыть вакансию</a>"
        )


class HHApi:
    def __init__(self):
        self.base_url = config.HH_API_URL
        self.headers = {
            "User-Agent": config.HH_USER_AGENT
        }
    
    async def _request(self, endpoint: str, params: dict = None) -> dict:
        """Базовый запрос к API"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers=self.headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {}
    
    async def search_vacancies(
        self,
        text: str,
        area: str = None,           # ID региона
        experience: str = None,      # noExperience, between1And3...
        schedule: str = None,        # remote, fullDay...
        salary: int = None,          # Минимальная зарплата
        only_with_salary: bool = False,
        page: int = 0,
        per_page: int = 5
    ) -> tuple[List[Vacancy], int]:
        """Поиск вакансий"""
        
        params = {
            "text": text,
            "page": page,
            "per_page": per_page,
            "order_by": "publication_time",  # Сначала новые
        }
        
        if area:
            params["area"] = area
        if experience:
            params["experience"] = experience
        if schedule:
            params["schedule"] = schedule
        if salary:
            params["salary"] = salary
        if only_with_salary:
            params["only_with_salary"] = "true"
        
        data = await self._request("/vacancies", params)
        
        if not data:
            return [], 0
        
        vacancies = []
        for item in data.get("items", []):
            vacancy = self._parse_vacancy(item)
            vacancies.append(vacancy)
        
        total = data.get("found", 0)
        return vacancies, total
    
    async def get_vacancy(self, vacancy_id: str) -> Optional[Vacancy]:
        """Получить конкретную вакансию"""
        data = await self._request(f"/vacancies/{vacancy_id}")
        if data:
            return self._parse_vacancy(data)
        return None
    
    async def get_salary_statistics(
        self,
        text: str,
        area: str = None
    ) -> Dict[str, Any]:
        """Получить статистику зарплат по запросу"""
        
        params = {
            "text": text,
            "only_with_salary": "true",
            "per_page": 100,
        }
        if area:
            params["area"] = area
        
        data = await self._request("/vacancies", params)
        
        if not data or not data.get("items"):
            return {"count": 0}
        
        salaries = []
        for item in data.get("items", []):
            salary = item.get("salary")
            if salary:
                # Приводим к рублям
                currency = salary.get("currency", "RUR")
                multiplier = {"RUR": 1, "USD": 90, "EUR": 100, "KZT": 0.2}.get(currency, 1)
                
                if salary.get("from"):
                    salaries.append(salary["from"] * multiplier)
                if salary.get("to"):
                    salaries.append(salary["to"] * multiplier)
        
        if not salaries:
            return {"count": 0}
        
        return {
            "count": len(data.get("items", [])),
            "total_found": data.get("found", 0),
            "min": int(min(salaries)),
            "max": int(max(salaries)),
            "avg": int(sum(salaries) / len(salaries)),
            "median": int(sorted(salaries)[len(salaries) // 2]),
        }
    
    async def get_areas(self) -> List[dict]:
        """Получить список регионов"""
        data = await self._request("/areas")
        return data if data else []
    
    async def suggest_areas(self, text: str) -> List[dict]:
        """Поиск региона по названию"""
        data = await self._request("/suggests/areas", {"text": text})
        return data.get("items", []) if data else []
    
    def _parse_vacancy(self, data: dict) -> Vacancy:
        """Парсинг вакансии из JSON"""
        salary = data.get("salary") or {}
        employer = data.get("employer") or {}
        address = data.get("address") or {}
        area = data.get("area") or {}
        experience = data.get("experience") or {}
        schedule = data.get("schedule") or {}
        snippet = data.get("snippet") or {}
        
        return Vacancy(
            id=data.get("id", ""),
            name=data.get("name", "Без названия"),
            url=data.get("alternate_url", ""),
            employer=employer.get("name", "Компания не указана"),
            employer_logo=employer.get("logo_urls", {}).get("90") if employer.get("logo_urls") else None,
            salary_from=salary.get("from"),
            salary_to=salary.get("to"),
            salary_currency=salary.get("currency"),
            city=address.get("city") or area.get("name", "Не указан"),
            experience=experience.get("name", "Не указан"),
            schedule=schedule.get("name", "Не указан"),
            requirement=snippet.get("requirement"),
            responsibility=snippet.get("responsibility"),
            published_at=data.get("published_at", ""),
        )


# Глобальный экземпляр
hh = HHApi()
