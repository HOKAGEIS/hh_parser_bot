# bot.py (исправленный код)
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import Config
import database as db
import keyboards as kb

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Проверка токена
if not Config.BOT_TOKEN or len(Config.BOT_TOKEN) < 40:
    print("❌ ОШИБКА: Токен бота не настроен!")
    exit(1)

# Инициализация
bot = Bot(
    token=Config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    logger.info(f"✅ /start от {message.from_user.id}")
    
    await db.ensure_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    
    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        "Я бот для поиска вакансий на <b>hh.ru</b> 🔍\n\n"
        "<b>Что я умею:</b>\n"
        "• 🔍 Искать вакансии с фильтрами\n"
        "• 📍 Поиск по городу\n"
        "• 💰 Фильтр по зарплате\n"
        "• 🚫 Исключать ненужные\n"
        "• ⭐ Избранное\n"
        "• 🔔 Подписки с уведомлениями\n"
        "• 🕐 История поиска\n"
        "• 📊 Аналитика\n\n"
        "Выберите действие 👇",
        reply_markup=kb.main_menu_kb(message.from_user.id)
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📚 <b>Справка</b>\n\n"
        "🔍 <b>Поиск</b> — искать вакансии\n"
        "⭐ <b>Избранное</b> — сохранённые\n"
        "🔔 <b>Подписки</b> — автоуведомления\n"
        "🕐 <b>История</b> — прошлые запросы\n"
        "📊 <b>Аналитика</b> — зарплаты\n"
        "⚙️ <b>Настройки</b> — параметры\n"
        "💬 <b>Поддержка</b> — помощь",
        reply_markup=kb.main_menu_kb(message.from_user.id)
    )


async def main():
    # Инициализация БД
    try:
        await db.init_db()  # Добавлен await
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка БД: {e}")
        return
    
    # Проверяем бота
    try:
        bot_info = await bot.get_me()
        logger.info(f"✅ Бот: @{bot_info.username}")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения: {e}")
        return
    
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Подключаем роутеры
    try:
        from handlers import search, favorites, subscriptions, settings, admin, support
        
        dp.include_router(search.router)
        dp.include_router(favorites.router)
        dp.include_router(subscriptions.router)
        dp.include_router(settings.router)
        dp.include_router(admin.router)
        dp.include_router(support.router)
        
        logger.info("✅ Роутеры подключены")
    except Exception as e:
        logger.error(f"❌ Ошибка роутеров: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Запускаем планировщик уведомлений
    try:
        from utils.scheduler import start_scheduler
        await start_scheduler(bot)
        logger.info("✅ Планировщик уведомлений запущен")
    except Exception as e:
        logger.warning(f"⚠️ Планировщик не запущен: {e}")
    
    logger.info("🚀 Бот запущен!")
    
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Бот остановлен")
