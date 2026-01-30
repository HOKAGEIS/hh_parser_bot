import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import config
import database as db
import keyboards as kb

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Проверка токена
if not config.BOT_TOKEN or len(config.BOT_TOKEN) < 40:
    print("❌ ОШИБКА: Токен бота не настроен!")
    exit(1)

# Инициализация бота и диспетчера
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


# ===== ОСНОВНЫЕ КОМАНДЫ =====

@dp.message(CommandStart())
async def cmd_start(message: Message):
    logger.info(f"✅ /start от {message.from_user.id}")
    
    await db.create_user(message.from_user.id, message.from_user.username)
    
    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        "Я бот для поиска вакансий на <b>hh.ru</b> 🔍\n\n"
        "<b>Что я умею:</b>\n"
        "• 🔍 Искать вакансии с фильтрами\n"
        "• 📍 Поиск по любому городу\n"
        "• 💰 Фильтр по зарплате\n"
        "• 🚫 Исключать ненужные вакансии\n"
        "• ⭐ Сохранять в избранное\n"
        "• 🔔 Подписки на новые вакансии\n"
        "• 📊 Аналитика зарплат\n\n"
        "Выберите действие 👇",
        reply_markup=kb.main_menu_kb()
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📚 <b>Справка</b>\n\n"
        "🔍 <b>Поиск</b> — поиск с фильтрами\n"
        "⭐ <b>Избранное</b> — сохранённые вакансии\n"
        "🔔 <b>Подписки</b> — уведомления о новых\n"
        "📊 <b>Аналитика</b> — статистика зарплат\n"
        "⚙️ <b>Настройки</b> — параметры поиска\n"
        "💬 <b>Поддержка</b> — связь с нами",
        reply_markup=kb.main_menu_kb()
    )


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("❌ Нет доступа")
        return
    
    import aiosqlite
    async with aiosqlite.connect(db.DATABASE) as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        
        cursor = await conn.execute("SELECT COUNT(*) FROM subscriptions WHERE active = 1")
        total_subs = (await cursor.fetchone())[0]
        
        cursor = await conn.execute("SELECT COUNT(*) FROM favorites")
        total_favs = (await cursor.fetchone())[0]
    
    await message.answer(
        "👑 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"🔔 Подписок: {total_subs}\n"
        f"⭐ В избранном: {total_favs}",
        reply_markup=kb.admin_kb()
    )


# ===== ЗАПУСК =====

async def main():
    # Инициализация БД
    try:
        await db.init_db()
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
    
    # Удаляем webhook
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Подключаем роутеры
    try:
        from handlers import search, favorites, subscriptions, settings
        
        dp.include_router(search.router)
        dp.include_router(favorites.router)
        dp.include_router(subscriptions.router)
        dp.include_router(settings.router)
        
        logger.info("✅ Роутеры подключены")
    except Exception as e:
        logger.error(f"❌ Ошибка роутеров: {e}")
        import traceback
        traceback.print_exc()
        return
    
    logger.info("🚀 Бот запущен!")
    
    # Запуск
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Бот остановлен")
