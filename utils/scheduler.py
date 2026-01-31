import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import database
import requests
from config import Config
from loguru import logger

class VacancyScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        
    async def check_new_vacancies(self):
        """Проверка новых вакансий по активным подпискам"""
        try:
            subscriptions = database.get_all_subscriptions()
            
            for user_id, query, filters_str in subscriptions:
                try:
                    # Преобразуем строку фильтров обратно в словарь
                    filters = {}
                    if filters_str and filters_str != 'None':
                        try:
                            filters = eval(filters_str)  # В продакшене лучше использовать json.loads
                            if isinstance(filters, str):
                                filters = {}
                        except:
                            filters = {}
                    
                    # Поиск новых вакансий
                    params = {'text': query, 'per_page': 5}
                    if 'city' in filters:
                        params['area'] = filters['city']
                    if 'salary' in filters:
                        params['salary'] = filters['salary']
                        params['only_with_salary'] = True
                    if 'experience' in filters:
                        params['experience'] = filters['experience']
                    if 'schedule' in filters:
                        params['schedule'] = filters['schedule']
                    if 'employment' in filters:
                        params['employment'] = filters['employment']
                    
                    response = requests.get(Config.HH_API_BASE_URL + '/vacancies', params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    
                    # Проверяем каждую вакансию
                    for item in data['items'][:3]:  # Проверяем только первые 3 вакансии
                        vacancy_id = item['id']
                        
                        # Проверяем, новая ли это вакансия для пользователя
                        if not database.is_favorite(user_id, vacancy_id):
                            # Отправляем уведомление пользователю
                            # Здесь должен быть код для отправки уведомления пользователю
                            # Пока просто логируем
                            logger.info(f"New vacancy for user {user_id}: {item['name']} at {item['employer']['name']}")
                            
                except Exception as e:
                    logger.error(f"Error checking vacancies for user {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in check_new_vacancies: {e}")
    
    def start(self):
        """Запуск планировщика"""
        try:
            self.scheduler.add_job(
                self.check_new_vacancies,
                trigger=IntervalTrigger(minutes=30),  # Проверять каждые 30 минут
                id='check_new_vacancies',
                name='Проверка новых вакансий по подписке'
            )
            
            self.scheduler.start()
            logger.info("Scheduler started successfully")
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
    
    def shutdown(self):
        """Остановка планировщика"""
        try:
            self.scheduler.shutdown()
            logger.info("Scheduler shut down successfully")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}")
