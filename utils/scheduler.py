import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import sqlite3
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

async def check_new_vacancies_for_subscribers(bot):
    """Проверка новых вакансий для подписчиков"""
    try:
        from hh_api import search_vacancies  # Предполагаем, что у вас есть такой модуль
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.user_id, s.query, s.filters
            FROM subscriptions s
            WHERE s.is_active = TRUE
        ''')
        subscriptions = cursor.fetchall()
        conn.close()
        
        for user_id, query, filters in subscriptions:
            try:
                # Здесь должен быть вызов API для поиска новых вакансий
                # vacancies = search_vacancies(query, filters, since_date=datetime.now().strftime('%Y-%m-%d'))
                
                # Пример отправки уведомления (раскомментируйте при наличии API)
                # for vacancy in vacancies:
                #     await bot.send_message(
                #         user_id,
                #         f"🔔 Новая вакансия по подписке:\n\n{vacancy['title']}\n{vacancy['company']}\n{vacancy['url']}"
                #     )
                
                pass  # Замените на реальную реализацию
                
            except Exception as e:
                logger.error(f"Error sending notification to {user_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in subscription checker: {e}")

async def start_scheduler(bot):
    """Запуск планировщика уведомлений"""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        func=lambda: asyncio.create_task(check_new_vacancies_for_subscribers(bot)),
        trigger=IntervalTrigger(minutes=30),  # Проверять каждые 30 минут
        id='subscription_checker',
        name='Check new vacancies for subscribers',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started")
