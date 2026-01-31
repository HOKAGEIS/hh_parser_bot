# database.py (добавлена функция get_open_ticket)
import aiosqlite
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from config import Config

# Путь к базе данных
DB_PATH = Path(Config.DATABASE_PATH)


async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DB_PATH) as db:
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
                settings TEXT DEFAULT '{}'
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
                FOREIGN KEY (user_id) REFERENCES users (user_id)
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
                FOREIGN KEY (user_id) REFERENCES users (user_id),
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
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица истории уведомлений
        await db.execute('''
            CREATE TABLE IF NOT EXISTS notification_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscription_id INTEGER,
                vacancy_id TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subscription_id) REFERENCES subscriptions (id)
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
                exclude_words TEXT,
                notifications_enabled BOOLEAN DEFAULT TRUE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
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
                FOREIGN KEY (user_id) REFERENCES users (user_id)
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
                FOREIGN KEY (ticket_id) REFERENCES tickets (id)
            )
        ''')
        
        await db.commit()


async def ensure_user(user_id: int, username: str = None, first_name: str = None, 
                     last_name: str = None, language_code: str = 'ru') -> None:
    """Создание или обновление пользователя"""
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
                INSERT INTO user_settings (user_id)
                VALUES (?)
            ''', (user_id,))
        
        await db.commit()


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Получение информации о пользователе"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_settings(user_id: int) -> Dict[str, Any]:
    """Получение настроек пользователя"""
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
                except:
                    settings['exclude_words'] = []
            return settings
        return {
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
            keys = ', '.join(kwargs.keys())
            placeholders = ', '.join(['?' for _ in kwargs])
            
            await db.execute(
                f'INSERT INTO user_settings ({keys}) VALUES ({placeholders})',
                list(kwargs.values())
            )
        
        await db.commit()


async def save_search_query(user_id: int, query: str, filters: Dict[str, Any]) -> None:
    """Сохранение поискового запроса"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO search_queries (user_id, query, filters)
            VALUES (?, ?, ?)
        ''', (user_id, query, json.dumps(filters, ensure_ascii=False)))
        await db.commit()


async def get_favorites(user_id: int) -> List[Dict[str, Any]]:
    """Получение избранных вакансий"""
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
                fav['vacancy_data'] = json.loads(fav['vacancy_data'])
            favorites.append(fav)
        
        return favorites


async def add_favorite(user_id: int, vacancy_id: str, vacancy_data: Dict[str, Any]) -> bool:
    """Добавление в избранное"""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute('''
                INSERT INTO favorites (user_id, vacancy_id, vacancy_data)
                VALUES (?, ?, ?)
            ''', (user_id, vacancy_id, json.dumps(vacancy_data, ensure_ascii=False)))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            # Вакансия уже в избранном
            return False


async def remove_favorite(user_id: int, vacancy_id: str) -> bool:
    """Удаление из избранного"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            DELETE FROM favorites 
            WHERE user_id = ? AND vacancy_id = ?
        ''', (user_id, vacancy_id))
        await db.commit()
        return cursor.rowcount > 0


async def is_favorite(user_id: int, vacancy_id: str) -> bool:
    """Проверка, находится ли вакансия в избранном"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            SELECT 1 FROM favorites 
            WHERE user_id = ? AND vacancy_id = ?
        ''', (user_id, vacancy_id))
        return await cursor.fetchone() is not None


async def get_subscriptions(user_id: int) -> List[Dict[str, Any]]:
    """Получение подписок пользователя"""
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
                sub['filters'] = json.loads(sub['filters'])
            subscriptions.append(sub)
        
        return subscriptions


async def add_subscription(user_id: int, name: str, query: str, filters: Dict[str, Any]) -> int:
    """Добавление подписки"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO subscriptions (user_id, name, query, filters)
            VALUES (?, ?, ?, ?)
        ''', (user_id, name, query, json.dumps(filters, ensure_ascii=False)))
        await db.commit()
        return cursor.lastrowid


async def delete_subscription(subscription_id: int) -> bool:
    """Удаление подписки"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            UPDATE subscriptions 
            SET is_active = FALSE 
            WHERE id = ?
        ''', (subscription_id,))
        await db.commit()
        return cursor.rowcount > 0


async def update_subscription_last_check(subscription_id: int) -> None:
    """Обновление времени последней проверки подписки"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            UPDATE subscriptions 
            SET last_check = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (subscription_id,))
        await db.commit()


async def get_active_subscriptions() -> List[Dict[str, Any]]:
    """Получение всех активных подписок для проверки"""
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
                sub['filters'] = json.loads(sub['filters'])
            subscriptions.append(sub)
        
        return subscriptions


async def add_notification_history(subscription_id: int, vacancy_id: str) -> None:
    """Добавление записи в историю уведомлений"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO notification_history (subscription_id, vacancy_id)
            VALUES (?, ?)
        ''', (subscription_id, vacancy_id))
        await db.commit()


async def was_notified(subscription_id: int, vacancy_id: str) -> bool:
    """Проверка, было ли уже отправлено уведомление о вакансии"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            SELECT 1 FROM notification_history 
            WHERE subscription_id = ? AND vacancy_id = ?
        ''', (subscription_id, vacancy_id))
        return await cursor.fetchone() is not None


async def get_statistics() -> Dict[str, int]:
    """Получение статистики для админов"""
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


async def get_open_ticket(user_id: int) -> Optional[Dict[str, Any]]:
    """Получение открытого тикета пользователя"""
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


async def create_ticket(user_id: int, username: str) -> int:
    """Создание нового тикета"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO tickets (user_id, username, status)
            VALUES (?, ?, 'open')
        ''', (user_id, username))
        await db.commit()
        return cursor.lastrowid


async def add_ticket_message(ticket_id: int, sender_type: str, message: str) -> None:
    """Добавление сообщения в тикет"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO ticket_messages (ticket_id, sender_type, message)
            VALUES (?, ?, ?)
        ''', (ticket_id, sender_type, message))
        await db.commit()


async def close_ticket(ticket_id: int) -> None:
    """Закрытие тикета"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            UPDATE tickets 
            SET status = 'closed', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (ticket_id,))
        await db.commit()


async def get_ticket_by_id(ticket_id: int) -> Optional[Dict[str, Any]]:
    """Получение тикета по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM tickets 
            WHERE id = ?
        ''', (ticket_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_ticket_messages(ticket_id: int) -> List[Dict[str, Any]]:
    """Получение сообщений тикета"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM ticket_messages 
            WHERE ticket_id = ?
            ORDER BY sent_at ASC
        ''', (ticket_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_all_open_tickets() -> List[Dict[str, Any]]:
    """Получение всех открытых тикетов"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM tickets 
            WHERE status = 'open'
            ORDER BY created_at DESC
        ''')
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
