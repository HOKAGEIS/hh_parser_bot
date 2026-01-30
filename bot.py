import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import config
import database as db
import keyboards as kb
from handlers import search, favorites, subscriptions, settings
# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Бот и диспетчер
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


# ==================== СТАРТ ====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await db.create_user(message.from_user.id, message.from_user.username)
    
    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        "Я бот для поиска вакансий на <b>hh.ru</b>\n\n"
        "🔍 <b>Что я умею:</b>\n"
        "• Искать вакансии с фильтрами\n"
        "• Сохранять в избранное\n"
        "• Уведомлять о новых вакансиях\n"
        "• Показывать статистику зарплат\n\n"
        "Выберите действие 👇",
        reply_markup=kb.main_menu_kb()
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📚 <b>Справка</b>\n\n"
        "🔍 <b>Поиск</b> — поиск вакансий с фильтрами\n"
        "⭐ <b>Избранное</b> — сохранённые вакансии\n"
        "🔔 <b>Подписки</b> — уведомления о новых\n"
        "📊 <b>Аналитика</b> — статистика зарплат\n"
        "⚙️ <b>Настройки</b> — параметры по умолчанию\n\n"
        "Есть вопросы? Пиши @your_username",
        reply_markup=kb.main_menu_kb()
    )


# ==================== ЗАПУСК ====================

async def main():
    # Инициализация БД
    await db.init_db()
    logger.info("Database initialized")
    
    # Подключение роутеров
    dp.include_router(search.router)
    dp.include_router(favorites.router)
    dp.include_router(subscriptions.router)
    dp.include_router(settings.router)
    
    # Запуск
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())



