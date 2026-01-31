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
    address: Optional[str] = None
    employer_accredited: bool = False
    
    @property
    def salary_text(self) -> str:
        if not self.salary_from and not self.salary_to:
            return "💰 Зарплата не указана"
        
        symbols = {"RUR": "₽", "USD": "$", "EUR": "€", "KZT": "₸"}
        symbol = symbols.get(self.salary_currency, self.salary_currency or "")
        
        if self.salary_from and self.salary_to:
            return f"💰 {self.salary_from:,} - {self.salary_to:,} {symbol}".replace(",", " ")
        elif self.salary_from:
            return f"💰 от {self.salary_from:,} {symbol}".replace(",", " ")
        else:
            return f"💰 до {self.salary_to:,} {symbol}".replace(",", " ")
    
    def to_short_message(self) -> str:
        req = self._clean_html(self.requirement or "")[:150]
        if len(req) == 150:
            req += "..."
        
        address_text = f"📍 {self.address}\n" if self.address else ""
        accredited = "✅ IT аккредитация\n" if self.employer_accredited else ""
        
        return (
            f"📌 <b>{self.name}</b>\n\n"
            f"🏢 {self.employer}\n"
            f"{accredited}"
            f"📍 {self.city}\n"
            f"{address_text}"
            f"{self.salary_text}\n"
            f"📋 Опыт: {self.experience}\n"
            f"⏰ {self.schedule}\n"
            f"💼 {self.employment}\n\n"
            f"📝 {req}\n\n"
            f"🔗 <a href='{self.url}'>Открыть на hh.ru</a>"
        )
    
    def _clean_html(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\n{2,}', '\n', text)
        return text.strip()


class HHApi:
    def __init__(self):
        
self.base_url = config.HH_API_BASE_URL
    
    async def _request(self, endpoint: str, params: dict = None) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers=self.headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {"error": response.status}
    
    async def search_vacancies(
        self,
        text: str,
        area: str = None,
        experience: str = None,
        schedule: str = None,
        employment: str = None,
        salary: int = None,
        only_with_salary: bool = False,
        exclude_words: List[str] = None,
        page: int = 0,
        per_page: int = 20,
        # Новые фильтры
        search_period: int = None,
        search_field: str = None,
        label: List[str] = None,
        education: str = None,
        accept_kids: bool = False,
        accept_handicapped: bool = False,
        accredited_it_employer: bool = False,
        with_address: bool = False,
        exclude_agency: bool = False,
    ) -> tuple[List[Vacancy], int]:
        
        # Формируем запрос с исключениями
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
        
        # Основные фильтры
        if area:
            params["area"] = area
        if experience:
            params["experience"] = experience
        if schedule:
            params["schedule"] = schedule
        if employment:
            params["employment"] = employment
        if salary:
            params["salary"] = salary
        if only_with_salary:
            params["only_with_salary"] = "true"
        
        # Период публикации
        if search_period and search_period > 0:
            params["search_period"] = search_period
        
        # Искать в
        if search_field:
            params["search_field"] = search_field
        
        # Образование
        if education:
            params["education"] = education
        
        # Специальные метки
        labels = []
        if accept_kids:
            labels.append("accept_kids")
        if accept_handicapped:
            labels.append("accept_handicapped")
        if accredited_it_employer:
            labels.append("accredited_it_employer")
        if labels:
            params["label"] = labels
        
        data = await self._request("/vacancies", params)
        
        if not data or "error" in data:
            return [], 0
        
        vacancies = []
        for item in data.get("items", []):
            # Фильтрация после получения
            if with_address and not item.get("address"):
                continue
            if exclude_agency:
                employer = item.get("employer", {})
                if employer.get("type") == "agency":
                    continue
            
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
        data = await self._request("/suggests/areas", {"text": city_name})
        if data and "items" in data:
            return data["items"]
        
        all_areas = await self._request("/areas")
        results = []
        
        def search_recursive(areas, query):
            for area in areas:
                if query.lower() in area.get("name", "").lower():
                    results.append({"id": area["id"], "text": area["name"]})
                if "areas" in area:
                    search_recursive(area["areas"], query)
        
        if all_areas:
            search_recursive(all_areas, city_name)
        
        return results[:10]
    
    async def get_salary_statistics(self, text: str, area: str = None) -> Dict[str, Any]:
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
    
    async def detect_city_by_ip(self) -> Optional[dict]:
        """Определение города по IP (для автоопределения)"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://ip-api.com/json/") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        city_name = data.get("city")
                        if city_name:
                            cities = await self.search_area(city_name)
                            if cities:
                                return cities[0]
        except Exception:
            pass
        return None
    
    def _parse_vacancy(self, data: dict) -> Vacancy:
        salary = data.get("salary") or {}
        employer = data.get("employer") or {}
        address = data.get("address") or {}
        area = data.get("area") or {}
        experience = data.get("experience") or {}
        schedule = data.get("schedule") or {}
        employment = data.get("employment") or {}
        snippet = data.get("snippet") or {}
        
        address_str = None
        if address:
            parts = []
            if address.get("city"):
                parts.append(address["city"])
            if address.get("street"):
                parts.append(address["street"])
            if address.get("building"):
                parts.append(address["building"])
            address_str = ", ".join(parts) if parts else None
        
        return Vacancy(
            id=data.get("id", ""),
            name=data.get("name", "Без названия"),
            url=data.get("alternate_url", ""),
            employer=employer.get("name", "Не указано"),
            employer_id=employer.get("id"),
            employer_logo=employer.get("logo_urls", {}).get("90") if employer.get("logo_urls") else None,
            salary_from=salary.get("from"),
            salary_to=salary.get("to"),
            salary_currency=salary.get("currency"),
            city=area.get("name", "Не указан"),
            experience=experience.get("name", "Не указан"),
            schedule=schedule.get("name", "Не указан"),
            employment=employment.get("name", "Не указана"),
            requirement=snippet.get("requirement"),
            responsibility=snippet.get("responsibility"),
            description=None,
            key_skills=[],
            published_at=data.get("published_at", ""),
            has_test=data.get("has_test", False),
            response_letter_required=data.get("response_letter_required", False),
            address=address_str,
            employer_accredited=employer.get("accredited_it_employer", False),
        )
    
    def _parse_vacancy_full(self, data: dict) -> Vacancy:
        vacancy = self._parse_vacancy(data)
        vacancy.description = data.get("description", "")
        vacancy.key_skills = [s.get("name", "") for s in data.get("key_skills", [])]
        return vacancy


hh = HHApi()

