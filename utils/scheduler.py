import asyncio
import logging
from datetime import datetime
from aiogram import Bot

import database as db
from hh_api import hh
from config import config

logger = logging.getLogger(__name__)


class NotificationScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running = False
        self.check_interval = 3600  # Проверка каждый час
    
    async def start(self):
        """Запуск планировщика"""
        self.running = True
        logger.info("🔔 Планировщик уведомлений запущен")
        
        while self.running:
            try:
                await self.check_subscriptions()
                await db.cleanup_old_notifications(days=7)
            except Exception as e:
                logger.error(f"Ошибка планировщика: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        """Остановка планировщика"""
        self.running = False
        logger.info("🔔 Планировщик уведомлений остановлен")
    
    async def check_subscriptions(self):
        """Проверка всех активных подписок"""
        logger.info("🔍 Проверяю подписки...")
        
        subscriptions = await db.get_all_active_subscriptions()
        
        for sub in subscriptions:
            try:
                await self.check_single_subscription(sub)
            except Exception as e:
                logger.error(f"Ошибка проверки подписки {sub.id}: {e}")
            
            # Небольшая пауза между запросами
            await asyncio.sleep(1)
        
        logger.info(f"✅ Проверено {len(subscriptions)} подписок")
    
    async def check_single_subscription(self, sub):
        """Проверка одной подписки"""
        
        # Проверяем, включены ли уведомления у пользователя
        user = await db.get_user(sub.user_id)
        if not user or not user.notifications_enabled:
            return
        
        # Получаем исключения
        exclude_words = []
        if sub.exclude_words:
            try:
                exclude_words = eval(sub.exclude_words) if isinstance(sub.exclude_words, str) else sub.exclude_words
            except:
                pass
        
        # Ищем новые вакансии
        vacancies, total = await hh.search_vacancies(
            text=sub.query,
            area=sub.city,
            experience=sub.experience,
            schedule=sub.schedule,
            salary=sub.min_salary,
            exclude_words=exclude_words,
            page=0,
            per_page=5,
            search_period=1  # Только за последние сутки
        )
        
        if not vacancies:
            await db.update_subscription_last_check(sub.id)
            return
        
        # Отправляем уведомления о новых вакансиях
        sent_count = 0
        for vacancy in vacancies[:3]:  # Максимум 3 вакансии за раз
            # Проверяем, отправляли ли уже
            if await db.was_notification_sent(sub.user_id, sub.id, vacancy.id):
                continue
            
            # Формируем сообщение
            text = (
                f"🔔 <b>Новая вакансия по подписке</b>\n"
                f"📝 <i>{sub.query}</i>\n\n"
                f"📌 <b>{vacancy.name}</b>\n"
                f"🏢 {vacancy.employer}\n"
                f"📍 {vacancy.city}\n"
                f"{vacancy.salary_text}\n\n"
                f"🔗 <a href='{vacancy.url}'>Открыть на hh.ru</a>"
            )
            
            try:
                await self.bot.send_message(
                    sub.user_id,
                    text,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                await db.mark_notification_sent(sub.user_id, sub.id, vacancy.id)
                sent_count += 1
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление {sub.user_id}: {e}")
        
        # Обновляем время проверки
        if vacancies:
            await db.update_subscription_last_check(sub.id, vacancies[0].id)
        
        if sent_count > 0:
            logger.info(f"📨 Отправлено {sent_count} уведомлений пользователю {sub.user_id}")


# Глобальный экземпляр
scheduler = None


async def start_scheduler(bot: Bot):
    """Запуск планировщика"""
    global scheduler
    scheduler = NotificationScheduler(bot)
    asyncio.create_task(scheduler.start())


async def stop_scheduler():
    """Остановка планировщика"""
    global scheduler
    if scheduler:
        await scheduler.stop()
