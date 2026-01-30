import aiohttp
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from config import config
import re


@dataclass
class Vacancy:
    id: str
    name: str
    url: str
    employer: str
    employer_id: Optional[str]
    employer_logo: Optional[str]
    salary_from: Optional[int]
    salary_to: Optional[int]
    salary_currency: Optional[str]
    city: str
    experience: str
    schedule: str
    employment: str
    requirement: Optional[str]
    responsibility: Optional[str]
    description: Optional[str]
    key_skills: List[str]
    published_at: str
    has_test: bool
    response_letter_required: bool
    
    @property
    def salary_text(self) -> str:
        if not self.salary_from and not self.salary_to:
            return "💰 Зарплата не указана"
        
        currency_symbols = {"RUR": "₽", "USD": "$", "EUR": "€", "KZT": "₸", "BYR": "Br"}
        symbol = currency_symbols.get(self.salary_currency, self.salary_currency or "")
        
        if self.salary_from and self.salary_to:
            return f"💰 {self.salary_from:,} - {self.salary_to:,} {symbol}".replace(",", " ")
        elif self.salary_from:
            return f"💰 от {self.salary_from:,} {symbol}".replace(",", " ")
        else:
            return f"💰 до {self.salary_to:,} {symbol}".replace(",", " ")
    
    def to_short_message(self) -> str:
        req = self.requirement or ""
        req = self._clean_html(req)
        if len(req) > 150:
            req = req[:150] + "..."
        
        return (
            f"📌 <b>{self.name}</b>\n\n"
            f"🏢 {self.employer}\n"
            f"📍 {self.city}\n"
            f"{self.salary_text}\n"
            f"📋 Опыт: {self.experience}\n"
            f"⏰ {self.schedule}\n\n"
            f"📝 {req}\n\n"
            f"🔗 <a href='{self.url}'>Открыть на hh.ru</a>"
        )
    
    def to_full_message(self) -> str:
        desc = self._clean_html(self.description or "Описание не указано")
        if len(desc) > 3000:
            desc = desc[:3000] + "...\n\n<i>Полное описание на hh.ru</i>"
        
        skills = ", ".join(self.key_skills[:10]) if self.key_skills else "Не указаны"
        
        return (
            f"📌 <b>{self.name}</b>\n\n"
            f"🏢 <b>Компания:</b> {self.employer}\n"
            f"📍 <b>Город:</b> {self.city}\n"
            f"{self.salary_text}\n"
            f"📋 <b>Опыт:</b> {self.experience}\n"
            f"⏰ <b>График:</b> {self.schedule}\n"
            f"💼 <b>Занятость:</b> {self.employment}\n\n"
            f"🛠 <b>Навыки:</b>\n{skills}\n\n"
            f"📝 <b>Описание:</b>\n{desc}\n\n"
            f"🔗 <a href='{self.url}'>Открыть на hh.ru</a>"
        )
    
    def _clean_html(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'<br\s*/?>', '\n', text)
        text = re.sub(r'<p>', '\n', text)
        text = re.sub(r'</p>', '', text)
        text = re.sub(r'<li>', '\n• ', text)
        text = re.sub(r'</li>', '', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'<highlighttext>', '', text)
        text = re.sub(r'</highlighttext>', '', text)
        return text.strip()


class HHApi:
    def __init__(self):
        self.base_url = config.HH_API_URL
        self.headers = {
            "User-Agent": config.HH_USER_AGENT
        }
    
    async def _request(self, endpoint: str, params: dict = None, method: str = "GET", 
                       data: dict = None, access_token: str = None) -> dict:
        headers = self.headers.copy()
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(
                    f"{self.base_url}{endpoint}",
                    params=params,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    return {"error": response.status}
            elif method == "POST":
                async with session.post(
                    f"{self.base_url}{endpoint}",
                    params=params,
                    json=data,
                    headers=headers
                ) as response:
                    return {"status": response.status, "data": await response.text()}
        return {}
    
    async def search_vacancies(
        self,
        text: str,
        area: str = None,
        experience: str = None,
        schedule: str = None,
        salary: int = None,
        only_with_salary: bool = False,
        exclude_words: List[str] = None,
        page: int = 0,
        per_page: int = 5
    ) -> tuple[List[Vacancy], int]:
        
        search_text = text
        if exclude_words:
            exclude_str = " ".join([f"NOT {word}" for word in exclude_words])
            search_text = f"{text} {exclude_str}"
        
        params = {
            "text": search_text,
            "page": page,
            "per_page": per_page,
            "order_by": "publication_time",
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
        
        if not data or "error" in data:
            return [], 0
        
        vacancies = []
        for item in data.get("items", []):
            vacancy = self._parse_vacancy(item)
            vacancies.append(vacancy)
        
        total = data.get("found", 0)
        return vacancies, total
    
    async def get_vacancy_full(self, vacancy_id: str) -> Optional[Vacancy]:
        data = await self._request(f"/vacancies/{vacancy_id}")
        if data and "error" not in data:
            return self._parse_vacancy_full(data)
        return None
    
    async def search_area(self, city_name: str) -> List[dict]:
        """Поиск города по названию"""
        data = await self._request("/suggests/areas", {"text": city_name})
        if data and "items" in data:
            return data["items"]
        
        all_areas = await self._request("/areas")
        results = []
        
        def search_recursive(areas, query):
            for area in areas:
                if query.lower() in area.get("name", "").lower():
                    results.append({
                        "id": area["id"],
                        "text": area["name"]
                    })
                if "areas" in area:
                    search_recursive(area["areas"], query)
        
        if all_areas:
            search_recursive(all_areas, city_name)
        
        return results[:10]
    
    async def get_salary_statistics(
        self,
        text: str,
        area: str = None,
        exclude_words: List[str] = None
    ) -> Dict[str, Any]:
        
        search_text = text
        if exclude_words:
            exclude_str = " ".join([f"NOT {word}" for word in exclude_words])
            search_text = f"{text} {exclude_str}"
        
        params = {
            "text": search_text,
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
    
    def _parse_vacancy(self, data: dict) -> Vacancy:
        salary = data.get("salary") or {}
        employer = data.get("employer") or {}
        address = data.get("address") or {}
        area = data.get("area") or {}
        experience = data.get("experience") or {}
        schedule = data.get("schedule") or {}
        employment = data.get("employment") or {}
        snippet = data.get("snippet") or {}
        
        return Vacancy(
            id=data.get("id", ""),
            name=data.get("name", "Без названия"),
            url=data.get("alternate_url", ""),
            employer=employer.get("name", "Компания не указана"),
            employer_id=employer.get("id"),
            employer_logo=employer.get("logo_urls", {}).get("90") if employer.get("logo_urls") else None,
            salary_from=salary.get("from"),
            salary_to=salary.get("to"),
            salary_currency=salary.get("currency"),
            city=address.get("city") or area.get("name", "Не указан"),
            experience=experience.get("name", "Не указан"),
            schedule=schedule.get("name", "Не указан"),
            employment=employment.get("name", "Не указан"),
            requirement=snippet.get("requirement"),
            responsibility=snippet.get("responsibility"),
            description=None,
            key_skills=[],
            published_at=data.get("published_at", ""),
            has_test=data.get("has_test", False),
            response_letter_required=data.get("response_letter_required", False),
        )
    
    def _parse_vacancy_full(self, data: dict) -> Vacancy:
        salary = data.get("salary") or {}
        employer = data.get("employer") or {}
        address = data.get("address") or {}
        area = data.get("area") or {}
        experience = data.get("experience") or {}
        schedule = data.get("schedule") or {}
        employment = data.get("employment") or {}
        
        key_skills = [skill.get("name", "") for skill in data.get("key_skills", [])]
        
        return Vacancy(
            id=data.get("id", ""),
            name=data.get("name", "Без названия"),
            url=data.get("alternate_url", ""),
            employer=employer.get("name", "Компания не указана"),
            employer_id=employer.get("id"),
            employer_logo=employer.get("logo_urls", {}).get("90") if employer.get("logo_urls") else None,
            salary_from=salary.get("from"),
            salary_to=salary.get("to"),
            salary_currency=salary.get("currency"),
            city=address.get("city") or area.get("name", "Не указан"),
            experience=experience.get("name", "Не указан"),
            schedule=schedule.get("name", "Не указан"),
            employment=employment.get("name", "Не указана"),
            requirement=None,
            responsibility=None,
            description=data.get("description", ""),
            key_skills=key_skills,
            published_at=data.get("published_at", ""),
            has_test=data.get("has_test", False),
            response_letter_required=data.get("response_letter_required", False),
        )


hh = HHApi()
