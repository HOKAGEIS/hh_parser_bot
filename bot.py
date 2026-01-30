import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import config
import database as db
import keyboards as kb

# Подробное логирование
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== ПРОВЕРКА ТОКЕНА =====
print("=" * 50)
print(f"BOT_TOKEN: {config.BOT_TOKEN[:10]}...{config.BOT_TOKEN[-5:] if len(config.BOT_TOKEN) > 15 else 'КОРОТКИЙ'}")
print(f"Token length: {len(config.BOT_TOKEN)}")
print("=" * 50)

if not config.BOT_TOKEN or config.BOT_TOKEN == "ВСТАВЬ_ТОКЕН" or "ВСТАВЬ" in config.BOT_TOKEN or len(config.BOT_TOKEN) < 40:
    print("❌ ОШИБКА: Токен бота не настроен!")
    print("Замените токен в config.py или переменных окружения")
    exit(1)

# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


# ===== ОСНОВНЫЕ КОМАНДЫ =====

@dp.message(CommandStart())
async def cmd_start(message: Message):
    logger.info(f"✅ /start от {message.from_user.id} (@{message.from_user.username})")
    print(f"✅ /start от {message.from_user.id} (@{message.from_user.username})")
    
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
        "• 📨 Откликаться на вакансии\n"
        "• ✉️ Сопроводительные письма\n"
        "• 📊 Аналитика зарплат\n\n"
        "Выберите действие 👇",
        reply_markup=kb.main_menu_kb()
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    logger.info(f"✅ /help от {message.from_user.id}")
    print(f"✅ /help от {message.from_user.id}")
    
    await message.answer(
        "📚 <b>Справка</b>\n\n"
        "🔍 <b>Поиск</b> — поиск с фильтрами\n"
        "⭐ <b>Избранное</b> — сохранённые вакансии\n"
        "🔔 <b>Подписки</b> — уведомления о новых\n"
        "📨 <b>Отклики</b> — история откликов\n"
        "✉️ <b>Письма</b> — шаблоны сопроводительных\n"
        "📊 <b>Аналитика</b> — статистика зарплат\n"
        "⚙️ <b>Настройки</b> — фильтры и HH.ru\n\n"
        "<b>Фильтры:</b>\n"
        "• Город — выбор или ввод вручную\n"
        "• Зарплата — выбор или своя сумма\n"
        "• Исключения — минус-слова",
        reply_markup=kb.main_menu_kb()
    )


@dp.message(Command("test"))
async def cmd_test(message: Message):
    print(f"✅ /test от {message.from_user.id}")
    await message.answer("✅ Бот работает корректно!")


# ===== ЗАПУСК =====

async def main():
    # Инициализация БД
    try:
        await db.init_db()
        print("✅ База данных инициализирована")
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Проверяем бота
    try:
        bot_info = await bot.get_me()
        print(f"✅ Бот: @{bot_info.username} (ID: {bot_info.id})")
    except Exception as e:
        print(f"❌ Ошибка подключения к Telegram: {e}")
        print("Проверьте токен бота!")
        return
    
    # Удаляем webhook (ВАЖНО для polling!)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook удалён, старые сообщения очищены")
    except Exception as e:
        print(f"⚠️ Ошибка удаления webhook: {e}")
    
    # Подключаем роутеры
    try:
        from handlers import search, favorites, subscriptions, settings, applications, cover_letters
        
        dp.include_router(search.router)
        print("  ✅ search.router подключен")
        
        dp.include_router(favorites.router)
        print("  ✅ favorites.router подключен")
        
        dp.include_router(subscriptions.router)
        print("  ✅ subscriptions.router подключен")
        
        dp.include_router(settings.router)
        print("  ✅ settings.router подключен")
        
        dp.include_router(applications.router)
        print("  ✅ applications.router подключен")
        
        dp.include_router(cover_letters.router)
        print("  ✅ cover_letters.router подключен")
        
        print("✅ Все роутеры подключены")
        
    except ImportError as e:
        print(f"❌ Ошибка импорта роутера: {e}")
        import traceback
        traceback.print_exc()
        return
    except Exception as e:
        print(f"❌ Ошибка подключения роутеров: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("=" * 50)
    print("🚀 БОТ УСПЕШНО ЗАПУЩЕН!")
    print(f"👤 Username: @{bot_info.username}")
    print("📨 Ожидаю сообщения...")
    print("=" * 50)
    
    # Запуск polling
    try:
        await dp.start_polling(
            bot, 
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True
        )
    except Exception as e:
        print(f"❌ Ошибка polling: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
