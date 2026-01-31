import aiosqlite
import json
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

DATABASE = "hh_bot.db"


@dataclass
class User:
    id: int
    username: Optional[str]
    default_city: Optional[str]
    default_city_name: Optional[str]
    default_experience: Optional[str]
    default_schedule: Optional[str]
    min_salary: Optional[int]
    only_with_salary: bool
    exclude_words: List[str]
    notifications_enabled: bool
    created_at: str


@dataclass
class Favorite:
    id: int
    user_id: int
    vacancy_id: str
    vacancy_data: dict
    added_at: str


@dataclass
class Subscription:
    id: int
    user_id: int
    query: str
    city: Optional[str]
    city_name: Optional[str]
    experience: Optional[str]
    schedule: Optional[str]
    min_salary: Optional[int]
    exclude_words: Optional[str]
    last_vacancy_id: Optional[str]
    last_check: Optional[str]
    active: bool
    created_at: str


async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DATABASE) as db:
        # Пользователи
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                default_city TEXT,
                default_city_name TEXT,
                default_experience TEXT,
                default_schedule TEXT,
                min_salary INTEGER,
                only_with_salary BOOLEAN DEFAULT 0,
                exclude_words TEXT DEFAULT '[]',
                notifications_enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Избранное
        await db.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                vacancy_id TEXT NOT NULL,
                vacancy_data TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, vacancy_id)
            )
        """)
        
        # Подписки
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                query TEXT NOT NULL,
                city TEXT,
                city_name TEXT,
                experience TEXT,
                schedule TEXT,
                min_salary INTEGER,
                exclude_words TEXT DEFAULT '[]',
                last_vacancy_id TEXT,
                last_check TIMESTAMP,
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # История поиска
        await db.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                query TEXT NOT NULL,
                city TEXT,
                city_name TEXT,
                filters TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Тикеты поддержки
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Сообщения в тикетах
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ticket_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                sender_type TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Отправленные уведомления (чтобы не дублировать)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sent_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subscription_id INTEGER NOT NULL,
                vacancy_id TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, subscription_id, vacancy_id)
            )
        """)
        
        await db.commit()
        print("✅ База данных инициализирована")


# ==================== ПОЛЬЗОВАТЕЛИ ====================

async def get_user(user_id: int) -> Optional[User]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            return User(
                id=row[0], username=row[1], default_city=row[2],
                default_city_name=row[3], default_experience=row[4],
                default_schedule=row[5], min_salary=row[6],
                only_with_salary=bool(row[7]),
                exclude_words=json.loads(row[8]) if row[8] else [],
                notifications_enabled=bool(row[9]) if len(row) > 9 else True,
                created_at=row[10] if len(row) > 10 else ""
            )
    return None


async def create_user(user_id: int, username: str = None):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (id, username, exclude_words) VALUES (?, ?, '[]')",
            (user_id, username)
        )
        await db.commit()


async def update_user_settings(user_id: int, **kwargs):
    async with aiosqlite.connect(DATABASE) as db:
        updates = []
        values = []
        
        field_map = {
            "city": "default_city",
            "city_name": "default_city_name",
            "experience": "default_experience",
            "schedule": "default_schedule",
            "min_salary": "min_salary",
            "only_with_salary": "only_with_salary",
            "exclude_words": "exclude_words",
            "notifications_enabled": "notifications_enabled",
        }
        
        for key, value in kwargs.items():
            if key in field_map:
                if key == "exclude_words" and isinstance(value, list):
                    value = json.dumps(value, ensure_ascii=False)
                updates.append(f"{field_map[key]} = ?")
                values.append(value)
        
        if updates:
            values.append(user_id)
            await db.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", values)
            await db.commit()


async def get_all_users_with_notifications() -> List[int]:
    """Получить всех пользователей с включёнными уведомлениями"""
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT id FROM users WHERE notifications_enabled = 1"
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


# ==================== ИСТОРИЯ ПОИСКА ====================

async def add_search_history(user_id: int, query: str, city: str = None, city_name: str = None, filters: dict = None):
    """Добавить запрос в историю"""
    async with aiosqlite.connect(DATABASE) as db:
        # Удаляем дубликаты
        await db.execute(
            "DELETE FROM search_history WHERE user_id = ? AND query = ?",
            (user_id, query)
        )
        
        # Добавляем новый
        await db.execute(
            "INSERT INTO search_history (user_id, query, city, city_name, filters) VALUES (?, ?, ?, ?, ?)",
            (user_id, query, city, city_name, json.dumps(filters or {}))
        )
        
        # Оставляем только последние 10
        await db.execute("""
            DELETE FROM search_history WHERE user_id = ? AND id NOT IN (
                SELECT id FROM search_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 10
            )
        """, (user_id, user_id))
        
        await db.commit()


async def get_search_history(user_id: int, limit: int = 10) -> List[dict]:
    """Получить историю поиска"""
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT query, city, city_name, filters, created_at FROM search_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
        rows = await cursor.fetchall()
        return [
            {
                "query": row[0],
                "city": row[1],
                "city_name": row[2],
                "filters": json.loads(row[3]) if row[3] else {},
                "created_at": row[4]
            }
            for row in rows
        ]


async def clear_search_history(user_id: int):
    """Очистить историю поиска"""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
        await db.commit()


# ==================== ИЗБРАННОЕ ====================

async def add_favorite(user_id: int, vacancy_id: str, vacancy_data: dict):
    async with aiosqlite.connect(DATABASE) as db:
        try:
            await db.execute(
                "INSERT INTO favorites (user_id, vacancy_id, vacancy_data) VALUES (?, ?, ?)",
                (user_id, vacancy_id, json.dumps(vacancy_data, ensure_ascii=False))
            )
            await db.commit()
            return True
        except:
            return False


async def remove_favorite(user_id: int, vacancy_id: str):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("DELETE FROM favorites WHERE user_id = ? AND vacancy_id = ?", (user_id, vacancy_id))
        await db.commit()


async def get_favorites(user_id: int) -> List[Favorite]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT id, user_id, vacancy_id, vacancy_data, added_at FROM favorites WHERE user_id = ? ORDER BY added_at DESC",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [Favorite(id=r[0], user_id=r[1], vacancy_id=r[2], vacancy_data=json.loads(r[3]), added_at=r[4]) for r in rows]


async def is_favorite(user_id: int, vacancy_id: str) -> bool:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT 1 FROM favorites WHERE user_id = ? AND vacancy_id = ?", (user_id, vacancy_id))
        return await cursor.fetchone() is not None


async def clear_favorites(user_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("DELETE FROM favorites WHERE user_id = ?", (user_id,))
        await db.commit()


# ==================== ПОДПИСКИ ====================

async def add_subscription(user_id: int, query: str, city: str = None, city_name: str = None,
                           experience: str = None, schedule: str = None, min_salary: int = None,
                           exclude_words: List[str] = None) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            """INSERT INTO subscriptions 
               (user_id, query, city, city_name, experience, schedule, min_salary, exclude_words) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, query, city, city_name, experience, schedule, min_salary, json.dumps(exclude_words or []))
        )
        await db.commit()
        return cursor.lastrowid


async def get_subscriptions(user_id: int, active_only: bool = True) -> List[Subscription]:
    async with aiosqlite.connect(DATABASE) as db:
        sql = "SELECT * FROM subscriptions WHERE user_id = ?"
        if active_only:
            sql += " AND active = 1"
        cursor = await db.execute(sql, (user_id,))
        rows = await cursor.fetchall()
        
        result = []
        for row in rows:
            result.append(Subscription(
                id=row[0], user_id=row[1], query=row[2], city=row[3],
                city_name=row[4], experience=row[5], schedule=row[6],
                min_salary=row[7], exclude_words=row[8],
                last_vacancy_id=row[9], last_check=row[10],
                active=bool(row[11]), created_at=row[12]
            ))
        return result


async def get_all_active_subscriptions() -> List[Subscription]:
    """Получить все активные подписки всех пользователей"""
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT * FROM subscriptions WHERE active = 1")
        rows = await cursor.fetchall()
        
        result = []
        for row in rows:
            result.append(Subscription(
                id=row[0], user_id=row[1], query=row[2], city=row[3],
                city_name=row[4], experience=row[5], schedule=row[6],
                min_salary=row[7], exclude_words=row[8],
                last_vacancy_id=row[9], last_check=row[10],
                active=bool(row[11]), created_at=row[12]
            ))
        return result


async def get_subscriptions_count(user_id: int) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM subscriptions WHERE user_id = ? AND active = 1", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0


async def delete_subscription(sub_id: int, user_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("DELETE FROM subscriptions WHERE id = ? AND user_id = ?", (sub_id, user_id))
        await db.commit()


async def toggle_subscription(sub_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT active FROM subscriptions WHERE id = ? AND user_id = ?", (sub_id, user_id))
        row = await cursor.fetchone()
        if row:
            new_status = not row[0]
            await db.execute("UPDATE subscriptions SET active = ? WHERE id = ?", (new_status, sub_id))
            await db.commit()
            return new_status
        return False


async def update_subscription_last_check(sub_id: int, last_vacancy_id: str = None):
    """Обновить время последней проверки подписки"""
    async with aiosqlite.connect(DATABASE) as db:
        if last_vacancy_id:
            await db.execute(
                "UPDATE subscriptions SET last_check = ?, last_vacancy_id = ? WHERE id = ?",
                (datetime.now().isoformat(), last_vacancy_id, sub_id)
            )
        else:
            await db.execute(
                "UPDATE subscriptions SET last_check = ? WHERE id = ?",
                (datetime.now().isoformat(), sub_id)
            )
        await db.commit()


# ==================== УВЕДОМЛЕНИЯ ====================

async def was_notification_sent(user_id: int, subscription_id: int, vacancy_id: str) -> bool:
    """Проверить, было ли отправлено уведомление"""
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT 1 FROM sent_notifications WHERE user_id = ? AND subscription_id = ? AND vacancy_id = ?",
            (user_id, subscription_id, vacancy_id)
        )
        return await cursor.fetchone() is not None


async def mark_notification_sent(user_id: int, subscription_id: int, vacancy_id: str):
    """Отметить уведомление как отправленное"""
    async with aiosqlite.connect(DATABASE) as db:
        try:
            await db.execute(
                "INSERT INTO sent_notifications (user_id, subscription_id, vacancy_id) VALUES (?, ?, ?)",
                (user_id, subscription_id, vacancy_id)
            )
            await db.commit()
        except:
            pass


async def cleanup_old_notifications(days: int = 7):
    """Удалить старые уведомления"""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "DELETE FROM sent_notifications WHERE sent_at < datetime('now', ?)",
            (f'-{days} days',)
        )
        await db.commit()


# ==================== ТИКЕТЫ ПОДДЕРЖКИ ====================

async def create_ticket(user_id: int, username: str = None) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("INSERT INTO tickets (user_id, username) VALUES (?, ?)", (user_id, username))
        await db.commit()
        return cursor.lastrowid


async def get_open_ticket(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT id, user_id, username, status, created_at FROM tickets WHERE user_id = ? AND status = 'open'",
            (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {"id": row[0], "user_id": row[1], "username": row[2], "status": row[3], "created_at": row[4]}
    return None


async def get_ticket_by_id(ticket_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT id, user_id, username, status, created_at FROM tickets WHERE id = ?", (ticket_id,))
        row = await cursor.fetchone()
        if row:
            return {"id": row[0], "user_id": row[1], "username": row[2], "status": row[3], "created_at": row[4]}
    return None


async def get_all_open_tickets() -> List[dict]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT id, user_id, username, status, created_at FROM tickets WHERE status = 'open' ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [{"id": r[0], "user_id": r[1], "username": r[2], "status": r[3], "created_at": r[4]} for r in rows]


async def close_ticket(ticket_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("UPDATE tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
        await db.commit()


async def add_ticket_message(ticket_id: int, sender_type: str, message: str):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("INSERT INTO ticket_messages (ticket_id, sender_type, message) VALUES (?, ?, ?)", (ticket_id, sender_type, message))
        await db.commit()


async def get_ticket_messages(ticket_id: int) -> List[dict]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT id, sender_type, message, created_at FROM ticket_messages WHERE ticket_id = ? ORDER BY created_at", (ticket_id,))
        rows = await cursor.fetchall()
        return [{"id": r[0], "sender_type": r[1], "message": r[2], "created_at": r[3]} for r in rows]
