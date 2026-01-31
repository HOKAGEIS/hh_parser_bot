# database.py (полностью исправленный код)
import aiosqlite
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from config import Config
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Путь к базе данных
DB_PATH = Path(Config.DATABASE_PATH)


async def init_db():
    """Инициализация базы данных"""
    try:
        # Создаём директорию если её нет
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiosqlite.connect(DB_PATH) as db:
            # Включаем поддержку foreign keys
            await db.execute("PRAGMA foreign_keys = ON")
            
            # Таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_premium BOOLEAN DEFAULT FALSE,
                    is_blocked BOOLEAN DEFAULT FALSE,
                    language_code TEXT DEFAULT 'ru',
                    settings TEXT DEFAULT '{}',
                    hh_access_token TEXT
                )
            ''')
            
            # Таблица поисковых запросов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS search_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    query TEXT,
                    filters TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            ''')
            
            # Таблица избранных вакансий
            await db.execute('''
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    vacancy_id TEXT,
                    vacancy_data TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    UNIQUE(user_id, vacancy_id)
                )
            ''')
            
            # Таблица подписок
            await db.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT,
                    query TEXT,
                    filters TEXT,
                    last_check TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    notification_time TEXT DEFAULT '10:00',
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            ''')
            
            # Таблица истории уведомлений
            await db.execute('''
                CREATE TABLE IF NOT EXISTS notification_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscription_id INTEGER,
                    vacancy_id TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subscription_id) REFERENCES subscriptions (id) ON DELETE CASCADE
                )
            ''')
            
            # Таблица настроек пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    city_id TEXT,
                    city_name TEXT,
                    experience TEXT,
                    schedule TEXT,
                    employment TEXT,
                    salary_from INTEGER,
                    only_with_salary BOOLEAN DEFAULT FALSE,
                    exclude_words TEXT DEFAULT '[]',
                    notifications_enabled BOOLEAN DEFAULT TRUE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            ''')
            
            # Таблица тикетов (для поддержки)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            ''')
            
            # Таблица сообщений тикетов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS ticket_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER,
                    sender_type TEXT, -- 'user' или 'support'
                    message TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets (id) ON DELETE CASCADE
                )
            ''')
            
            # Таблица откликов на вакансии
            await db.execute('''
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    vacancy_id TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'sent',
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    UNIQUE(user_id, vacancy_id)
                )
            ''')
            
            # Создаём индексы для ускорения запросов
            await db.execute('CREATE INDEX IF NOT EXISTS idx_search_user_id ON search_queries(user_id)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites(user_id)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON tickets(user_id)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)')
            
            await db.commit()
            logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise


async def ensure_user(user_id: int, username: str = None, first_name: str = None, 
                     last_name: str = None, language_code: str = 'ru') -> None:
    """Создание или обновление пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем существует ли пользователь
            cursor = await db.execute(
                'SELECT user_id FROM users WHERE user_id = ?',
                (user_id,)
            )
            exists = await cursor.fetchone()
            
            if exists:
                # Обновляем последнюю активность
                await db.execute('''
                    UPDATE users 
                    SET last_active = CURRENT_TIMESTAMP,
                        username = COALESCE(?, username),
                        first_name = COALESCE(?, first_name),
                        last_name = COALESCE(?, last_name)
                    WHERE user_id = ?
                ''', (username, first_name, last_name, user_id))
            else:
                # Создаём нового пользователя
                await db.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, language_code)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name, language_code))
                
                # Создаём настройки по умолчанию
                await db.execute('''
                    INSERT OR IGNORE INTO user_settings (user_id, exclude_words)
                    VALUES (?, '[]')
                ''', (user_id,))
            
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при создании/обновлении пользователя {user_id}: {e}")
        raise


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Получение информации о пользователе"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM users WHERE user_id = ?',
                (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя {user_id}: {e}")
        return None


async def get_user_settings(user_id: int) -> Dict[str, Any]:
    """Получение настроек пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM user_settings WHERE user_id = ?',
                (user_id,)
            )
            row = await cursor.fetchone()
            if row:
                settings = dict(row)
                # Преобразуем exclude_words из JSON строки в список
                if settings.get('exclude_words'):
                    try:
                        settings['exclude_words'] = json.loads(settings['exclude_words'])
                    except (json.JSONDecodeError, TypeError):
                        settings['exclude_words'] = []
                else:
                    settings['exclude_words'] = []
                return settings
            
            # Возвращаем настройки по умолчанию
            return {
                'user_id': user_id,
                'city_id': None,
                'city_name': None,
                'experience': None,
                'schedule': None,
                'employment': None,
                'salary_from': None,
                'only_with_salary': False,
                'exclude_words': [],
                'notifications_enabled': True
            }
    except Exception as e:
        logger.error(f"Ошибка при получении настроек пользователя {user_id}: {e}")
        # Возвращаем настройки по умолчанию при ошибке
        return {
            'user_id': user_id,
            'city_id': None,
            'city_name': None,
            'experience': None,
            'schedule': None,
            'employment': None,
            'salary_from': None,
            'only_with_salary': False,
            'exclude_words': [],
            'notifications_enabled': True
        }


async def update_user_settings(user_id: int, **kwargs) -> None:
    """Обновление настроек пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем существуют ли настройки
            cursor = await db.execute(
                'SELECT user_id FROM user_settings WHERE user_id = ?',
                (user_id,)
            )
            exists = await cursor.fetchone()
            
            # Преобразуем exclude_words в JSON если это список
            if 'exclude_words' in kwargs and isinstance(kwargs['exclude_words'], list):
                kwargs['exclude_words'] = json.dumps(kwargs['exclude_words'], ensure_ascii=False)
            
            if exists:
                # Обновляем существующие настройки
                set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
                set_clause += ', updated_at = CURRENT_TIMESTAMP'
                values = list(kwargs.values()) + [user_id]
                
                await db.execute(
                    f'UPDATE user_settings SET {set_clause} WHERE user_id = ?',
                    values
                )
            else:
                # Создаём новые настройки
                kwargs['user_id'] = user_id
                # Устанавливаем значение по умолчанию для exclude_words если не передано
                if 'exclude_words' not in kwargs:
                    kwargs['exclude_words'] = '[]'
                    
                keys = ', '.join(kwargs.keys())
                placeholders = ', '.join(['?' for _ in kwargs])
                
                await db.execute(
                    f'INSERT INTO user_settings ({keys}) VALUES ({placeholders})',
                    list(kwargs.values())
                )
            
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при обновлении настроек пользователя {user_id}: {e}")
        raise


async def save_search_query(user_id: int, query: str, filters: Dict[str, Any]) -> None:
    """Сохранение поискового запроса"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT INTO search_queries (user_id, query, filters)
                VALUES (?, ?, ?)
            ''', (user_id, query, json.dumps(filters, ensure_ascii=False)))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при сохранении поискового запроса для пользователя {user_id}: {e}")


async def get_favorites(user_id: int) -> List[Dict[str, Any]]:
    """Получение избранных вакансий"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM favorites 
                WHERE user_id = ? 
                ORDER BY added_at DESC
            ''', (user_id,))
            rows = await cursor.fetchall()
            
            favorites = []
            for row in rows:
                fav = dict(row)
                if fav['vacancy_data']:
                    try:
                        fav['vacancy_data'] = json.loads(fav['vacancy_data'])
                    except (json.JSONDecodeError, TypeError):
                        fav['vacancy_data'] = {}
                favorites.append(fav)
            
            return favorites
    except Exception as e:
        logger.error(f"Ошибка при получении избранного для пользователя {user_id}: {e}")
        return []


async def add_favorite(user_id: int, vacancy_id: str, vacancy_data: Dict[str, Any]) -> bool:
    """Добавление в избранное"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT INTO favorites (user_id, vacancy_id, vacancy_data)
                VALUES (?, ?, ?)
            ''', (user_id, vacancy_id, json.dumps(vacancy_data, ensure_ascii=False)))
            await db.commit()
            return True
    except aiosqlite.IntegrityError:
        # Вакансия уже в избранном
        return False
    except Exception as e:
        logger.error(f"Ошибка при добавлении в избранное для пользователя {user_id}: {e}")
        return False


async def remove_favorite(user_id: int, vacancy_id: str) -> bool:
    """Удаление из избранного"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('''
                DELETE FROM favorites 
                WHERE user_id = ? AND vacancy_id = ?
            ''', (user_id, vacancy_id))
            await db.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Ошибка при удалении из избранного для пользователя {user_id}: {e}")
        return False


async def is_favorite(user_id: int, vacancy_id: str) -> bool:
    """Проверка, находится ли вакансия в избранном"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('''
                SELECT 1 FROM favorites 
                WHERE user_id = ? AND vacancy_id = ?
            ''', (user_id, vacancy_id))
            return await cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Ошибка при проверке избранного для пользователя {user_id}: {e}")
        return False


async def get_subscriptions(user_id: int) -> List[Dict[str, Any]]:
    """Получение подписок пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM subscriptions 
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY created_at DESC
            ''', (user_id,))
            rows = await cursor.fetchall()
            
            subscriptions = []
            for row in rows:
                sub = dict(row)
                if sub['filters']:
                    try:
                        sub['filters'] = json.loads(sub['filters'])
                    except (json.JSONDecodeError, TypeError):
                        sub['filters'] = {}
                subscriptions.append(sub)
            
            return subscriptions
    except Exception as e:
        logger.error(f"Ошибка при получении подписок для пользователя {user_id}: {e}")
        return []


async def add_subscription(user_id: int, name: str, query: str, filters: Dict[str, Any]) -> Optional[int]:
    """Добавление подписки"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('''
                INSERT INTO subscriptions (user_id, name, query, filters)
                VALUES (?, ?, ?, ?)
            ''', (user_id, name, query, json.dumps(filters, ensure_ascii=False)))
            await db.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Ошибка при добавлении подписки для пользователя {user_id}: {e}")
        return None


async def delete_subscription(subscription_id: int) -> bool:
    """Удаление подписки"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('''
                UPDATE subscriptions 
                SET is_active = FALSE 
                WHERE id = ?
            ''', (subscription_id,))
            await db.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Ошибка при удалении подписки {subscription_id}: {e}")
        return False


async def update_subscription_last_check(subscription_id: int) -> None:
    """Обновление времени последней проверки подписки"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                UPDATE subscriptions 
                SET last_check = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (subscription_id,))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при обновлении времени проверки подписки {subscription_id}: {e}")


async def get_active_subscriptions() -> List[Dict[str, Any]]:
    """Получение всех активных подписок для проверки"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT s.*, u.language_code 
                FROM subscriptions s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.is_active = TRUE
            ''')
            rows = await cursor.fetchall()
            
            subscriptions = []
            for row in rows:
                sub = dict(row)
                if sub['filters']:
                    try:
                        sub['filters'] = json.loads(sub['filters'])
                    except (json.JSONDecodeError, TypeError):
                        sub['filters'] = {}
                subscriptions.append(sub)
            
            return subscriptions
    except Exception as e:
        logger.error(f"Ошибка при получении активных подписок: {e}")
        return []


async def add_notification_history(subscription_id: int, vacancy_id: str) -> None:
    """Добавление записи в историю уведомлений"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT INTO notification_history (subscription_id, vacancy_id)
                VALUES (?, ?)
            ''', (subscription_id, vacancy_id))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при добавлении истории уведомления для подписки {subscription_id}: {e}")


async def was_notified(subscription_id: int, vacancy_id: str) -> bool:
    """Проверка, было ли уже отправлено уведомление о вакансии"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('''
                SELECT 1 FROM notification_history 
                WHERE subscription_id = ? AND vacancy_id = ?
            ''', (subscription_id, vacancy_id))
            return await cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Ошибка при проверке истории уведомлений для подписки {subscription_id}: {e}")
        return False


async def get_statistics() -> Dict[str, int]:
    """Получение статистики для админов"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            stats = {}
            
            # Количество пользователей
            cursor = await db.execute('SELECT COUNT(*) FROM users')
            stats['total_users'] = (await cursor.fetchone())[0]
            
            # Активные пользователи за последние 7 дней
            cursor = await db.execute('''
                SELECT COUNT(*) FROM users 
                WHERE last_active > datetime('now', '-7 days')
            ''')
            stats['active_users'] = (await cursor.fetchone())[0]
            
            # Количество поисков
            cursor = await db.execute('SELECT COUNT(*) FROM search_queries')
            stats['total_searches'] = (await cursor.fetchone())[0]
            
            # Количество избранных
            cursor = await db.execute('SELECT COUNT(*) FROM favorites')
            stats['total_favorites'] = (await cursor.fetchone())[0]
            
            # Количество подписок
            cursor = await db.execute('SELECT COUNT(*) FROM subscriptions WHERE is_active = TRUE')
            stats['active_subscriptions'] = (await cursor.fetchone())[0]
            
            return stats
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        return {
            'total_users': 0,
            'active_users': 0,
            'total_searches': 0,
            'total_favorites': 0,
            'active_subscriptions': 0
        }


async def get_open_ticket(user_id: int) -> Optional[Dict[str, Any]]:
    """Получение открытого тикета пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM tickets 
                WHERE user_id = ? AND status = 'open'
                ORDER BY created_at DESC
                LIMIT 1
            ''', (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Ошибка при получении открытого тикета для пользователя {user_id}: {e}")
        return None


async def create_ticket(user_id: int, username: str) -> Optional[int]:
    """Создание нового тикета"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('''
                INSERT INTO tickets (user_id, username, status)
                VALUES (?, ?, 'open')
            ''', (user_id, username))
            await db.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Ошибка при создании тикета для пользователя {user_id}: {e}")
        return None


async def add_ticket_message(ticket_id: int, sender_type: str, message: str) -> None:
    """Добавление сообщения в тикет"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT INTO ticket_messages (ticket_id, sender_type, message)
                VALUES (?, ?, ?)
            ''', (ticket_id, sender_type, message))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при добавлении сообщения в тикет {ticket_id}: {e}")


async def close_ticket(ticket_id: int) -> None:
    """Закрытие тикета"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                UPDATE tickets 
                SET status = 'closed', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (ticket_id,))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при закрытии тикета {ticket_id}: {e}")


async def get_ticket_by_id(ticket_id: int) -> Optional[Dict[str, Any]]:
    """Получение тикета по ID"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM tickets 
                WHERE id = ?
            ''', (ticket_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Ошибка при получении тикета {ticket_id}: {e}")
        return None


async def get_ticket_messages(ticket_id: int) -> List[Dict[str, Any]]:
    """Получение сообщений тикета"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM ticket_messages 
                WHERE ticket_id = ?
                ORDER BY sent_at ASC
            ''', (ticket_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений тикета {ticket_id}: {e}")
        return []


async def get_all_open_tickets() -> List[Dict[str, Any]]:
    """Получение всех открытых тикетов"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM tickets 
                WHERE status = 'open'
                ORDER BY created_at DESC
            ''')
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Ошибка при получении открытых тикетов: {e}")
        return []


# --- Новые функции для поиска ---
async def add_search_history(user_id: int, query: str, filters: Dict[str, Any]) -> None:
    """Добавление записи в историю поиска"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT INTO search_queries (user_id, query, filters)
                VALUES (?, ?, ?)
            ''', (user_id, query, json.dumps(filters, ensure_ascii=False)))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при добавлении в историю поиска для пользователя {user_id}: {e}")


async def get_search_history(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Получение истории поиска пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT query, filters, created_at FROM search_queries 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (user_id, limit))
            rows = await cursor.fetchall()
            
            history = []
            for row in rows:
                record = dict(row)
                if record['filters']:
                    try:
                        record['filters'] = json.loads(record['filters'])
                    except (json.JSONDecodeError, TypeError):
                        record['filters'] = {}
                else:
                    record['filters'] = {}
                        
                # Добавляем поля city и city_name из filters для совместимости с keyboards.py
                filters_data = record['filters']
                record['city'] = filters_data.get('city')
                record['city_name'] = filters_data.get('city_name', '')
                
                history.append(record)
            
            return history
    except Exception as e:
        logger.error(f"Ошибка при получении истории поиска для пользователя {user_id}: {e}")
        return []


async def was_applied(user_id: int, vacancy_id: str) -> bool:
    """Проверка, откликался ли пользователь на вакансию"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('''
                SELECT 1 FROM applications 
                WHERE user_id = ? AND vacancy_id = ?
            ''', (user_id, vacancy_id))
            return await cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Ошибка при проверке отклика пользователя {user_id} на вакансию {vacancy_id}: {e}")
        return False


async def add_application(user_id: int, vacancy_id: str) -> bool:
    """Добавление записи об отклике на вакансию"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT INTO applications (user_id, vacancy_id)
                VALUES (?, ?)
            ''', (user_id, vacancy_id))
            await db.commit()
            return True
    except aiosqlite.IntegrityError:
        # Уже откликался
        return False
    except Exception as e:
        logger.error(f"Ошибка при добавлении отклика пользователя {user_id} на вакансию {vacancy_id}: {e}")
        return False


async def get_subscriptions_count(user_id: int) -> int:
    """Получение количества подписок пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('''
                SELECT COUNT(*) FROM subscriptions 
                WHERE user_id = ? AND is_active = TRUE
            ''', (user_id,))
            count = (await cursor.fetchone())[0]
            return count
    except Exception as e:
        logger.error(f"Ошибка при подсчете подписок для пользователя {user_id}: {e}")
        return 0


async def clear_search_history(user_id: int) -> None:
    """Очистка истории поиска пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('DELETE FROM search_queries WHERE user_id = ?', (user_id,))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при очистке истории поиска для пользователя {user_id}: {e}")
