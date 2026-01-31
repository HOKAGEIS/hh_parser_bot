import aiosqlite
import json
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

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
    # OAuth
    hh_access_token: Optional[str]
    hh_refresh_token: Optional[str]
    hh_token_expires: Optional[str]
    default_resume_id: Optional[str]
    cover_letter_template: Optional[str]
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
                hh_access_token TEXT,
                hh_refresh_token TEXT,
                hh_token_expires TEXT,
                default_resume_id TEXT,
                cover_letter_template TEXT,
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
                FOREIGN KEY (user_id) REFERENCES users(id),
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
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # История откликов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                vacancy_id TEXT NOT NULL,
                vacancy_name TEXT,
                employer TEXT,
                status TEXT DEFAULT 'sent',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Сопроводительные письма (шаблоны)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cover_letters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                text TEXT NOT NULL,
                is_default BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        await db.commit()

async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DATABASE) as db:
        # ... существующие таблицы ...
        
        # Тикеты поддержки
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Сообщения в тикетах
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ticket_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                sender_type TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets(id)
            )
        """)
        
        await db.commit()


# ==================== ПОЛЬЗОВАТЕЛИ ====================

async def get_user(user_id: int) -> Optional[User]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return User(
                id=row[0],
                username=row[1],
                default_city=row[2],
                default_city_name=row[3],
                default_experience=row[4],
                default_schedule=row[5],
                min_salary=row[6],
                only_with_salary=bool(row[7]),
                exclude_words=json.loads(row[8]) if row[8] else [],
                hh_access_token=row[9],
                hh_refresh_token=row[10],
                hh_token_expires=row[11],
                default_resume_id=row[12],
                cover_letter_template=row[13],
                created_at=row[14]
            )
    return None

async def create_user(user_id: int, username: str = None):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            """INSERT OR IGNORE INTO users (id, username, exclude_words) 
               VALUES (?, ?, '[]')""",
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
            "hh_access_token": "hh_access_token",
            "hh_refresh_token": "hh_refresh_token",
            "hh_token_expires": "hh_token_expires",
            "default_resume_id": "default_resume_id",
            "cover_letter_template": "cover_letter_template",
        }
        
        for key, value in kwargs.items():
            if key in field_map and value is not None:
                db_field = field_map[key]
                if key == "exclude_words" and isinstance(value, list):
                    value = json.dumps(value, ensure_ascii=False)
                updates.append(f"{db_field} = ?")
                values.append(value)
        
        if updates:
            values.append(user_id)
            await db.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
                values
            )
            await db.commit()


# ==================== ИСКЛЮЧЕНИЯ ====================

async def add_exclude_word(user_id: int, word: str) -> bool:
    user = await get_user(user_id)
    if not user:
        return False
    
    words = user.exclude_words or []
    if word.lower() not in [w.lower() for w in words]:
        words.append(word.lower())
        await update_user_settings(user_id, exclude_words=words)
        return True
    return False

async def remove_exclude_word(user_id: int, word: str) -> bool:
    user = await get_user(user_id)
    if not user:
        return False
    
    words = user.exclude_words or []
    words_lower = [w.lower() for w in words]
    if word.lower() in words_lower:
        idx = words_lower.index(word.lower())
        words.pop(idx)
        await update_user_settings(user_id, exclude_words=words)
        return True
    return False

async def get_exclude_words(user_id: int) -> List[str]:
    user = await get_user(user_id)
    return user.exclude_words if user else []


# ==================== ИЗБРАННОЕ ====================

async def add_favorite(user_id: int, vacancy_id: str, vacancy_data: dict):
    async with aiosqlite.connect(DATABASE) as db:
        try:
            await db.execute(
                """INSERT INTO favorites (user_id, vacancy_id, vacancy_data)
                   VALUES (?, ?, ?)""",
                (user_id, vacancy_id, json.dumps(vacancy_data, ensure_ascii=False))
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def remove_favorite(user_id: int, vacancy_id: str):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "DELETE FROM favorites WHERE user_id = ? AND vacancy_id = ?",
            (user_id, vacancy_id)
        )
        await db.commit()

async def get_favorites(user_id: int) -> List[Favorite]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            """SELECT id, user_id, vacancy_id, vacancy_data, added_at 
               FROM favorites WHERE user_id = ? ORDER BY added_at DESC""",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [
            Favorite(
                id=row[0],
                user_id=row[1],
                vacancy_id=row[2],
                vacancy_data=json.loads(row[3]),
                added_at=row[4]
            )
            for row in rows
        ]

async def is_favorite(user_id: int, vacancy_id: str) -> bool:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND vacancy_id = ?",
            (user_id, vacancy_id)
        )
        return await cursor.fetchone() is not None


# ==================== ПОДПИСКИ ====================

async def add_subscription(
    user_id: int,
    query: str,
    city: str = None,
    city_name: str = None,
    experience: str = None,
    schedule: str = None,
    min_salary: int = None,
    exclude_words: List[str] = None
) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            """INSERT INTO subscriptions 
               (user_id, query, city, city_name, experience, schedule, min_salary, exclude_words)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, query, city, city_name, experience, schedule, min_salary,
             json.dumps(exclude_words or [], ensure_ascii=False))
        )
        await db.commit()
        return cursor.lastrowid

async def get_subscriptions(user_id: int, active_only: bool = True) -> List[Subscription]:
    async with aiosqlite.connect(DATABASE) as db:
        if active_only:
            cursor = await db.execute(
                "SELECT * FROM subscriptions WHERE user_id = ? AND active = 1",
                (user_id,)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM subscriptions WHERE user_id = ?",
                (user_id,)
            )
        rows = await cursor.fetchall()
        return [Subscription(*row) for row in rows]

async def get_subscriptions_count(user_id: int) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM subscriptions WHERE user_id = ? AND active = 1",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

async def delete_subscription(sub_id: int, user_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "DELETE FROM subscriptions WHERE id = ? AND user_id = ?",
            (sub_id, user_id)
        )
        await db.commit()

async def toggle_subscription(sub_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT active FROM subscriptions WHERE id = ? AND user_id = ?",
            (sub_id, user_id)
        )
        row = await cursor.fetchone()
        if row:
            new_status = not row[0]
            await db.execute(
                "UPDATE subscriptions SET active = ? WHERE id = ?",
                (new_status, sub_id)
            )
            await db.commit()
            return new_status
        return False


# ==================== СОПРОВОДИТЕЛЬНЫЕ ПИСЬМА ====================

async def add_cover_letter(user_id: int, name: str, text: str, is_default: bool = False) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        if is_default:
            await db.execute(
                "UPDATE cover_letters SET is_default = 0 WHERE user_id = ?",
                (user_id,)
            )
        
        cursor = await db.execute(
            "INSERT INTO cover_letters (user_id, name, text, is_default) VALUES (?, ?, ?, ?)",
            (user_id, name, text, is_default)
        )
        await db.commit()
        return cursor.lastrowid

async def get_cover_letters(user_id: int) -> List[dict]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT id, name, text, is_default FROM cover_letters WHERE user_id = ? ORDER BY is_default DESC",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [{"id": r[0], "name": r[1], "text": r[2], "is_default": r[3]} for r in rows]

async def get_cover_letter(letter_id: int, user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT id, name, text, is_default FROM cover_letters WHERE id = ? AND user_id = ?",
            (letter_id, user_id)
        )
        row = await cursor.fetchone()
        if row:
            return {"id": row[0], "name": row[1], "text": row[2], "is_default": row[3]}
    return None

async def delete_cover_letter(letter_id: int, user_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "DELETE FROM cover_letters WHERE id = ? AND user_id = ?",
            (letter_id, user_id)
        )
        await db.commit()

async def set_default_cover_letter(letter_id: int, user_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "UPDATE cover_letters SET is_default = 0 WHERE user_id = ?",
            (user_id,)
        )
        await db.execute(
            "UPDATE cover_letters SET is_default = 1 WHERE id = ? AND user_id = ?",
            (letter_id, user_id)
        )
        await db.commit()

async def get_default_cover_letter(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT id, name, text FROM cover_letters WHERE user_id = ? AND is_default = 1",
            (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {"id": row[0], "name": row[1], "text": row[2]}
    return None


# ==================== ОТКЛИКИ ====================

async def add_application(user_id: int, vacancy_id: str, vacancy_name: str, employer: str):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT INTO applications (user_id, vacancy_id, vacancy_name, employer) VALUES (?, ?, ?, ?)",
            (user_id, vacancy_id, vacancy_name, employer)
        )
        await db.commit()

async def get_applications(user_id: int, limit: int = 20) -> List[dict]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            """SELECT vacancy_id, vacancy_name, employer, status, applied_at 
               FROM applications WHERE user_id = ? ORDER BY applied_at DESC LIMIT ?""",
            (user_id, limit)
        )
        rows = await cursor.fetchall()
        return [
            {
                "vacancy_id": r[0],
                "vacancy_name": r[1],
                "employer": r[2],
                "status": r[3],
                "applied_at": r[4]
            }
            for r in rows
        ]

async def was_applied(user_id: int, vacancy_id: str) -> bool:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT 1 FROM applications WHERE user_id = ? AND vacancy_id = ?",
            (user_id, vacancy_id)
        )
        return await cursor.fetchone() is not None

# ==================== ТИКЕТЫ ПОДДЕРЖКИ ====================

async def create_ticket(user_id: int, username: str = None) -> int:
    """Создать новый тикет"""
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "INSERT INTO tickets (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await db.commit()
        return cursor.lastrowid


async def get_open_ticket(user_id: int) -> Optional[dict]:
    """Получить открытый тикет пользователя"""
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
    """Получить тикет по ID"""
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT id, user_id, username, status, created_at FROM tickets WHERE id = ?",
            (ticket_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {"id": row[0], "user_id": row[1], "username": row[2], "status": row[3], "created_at": row[4]}
    return None


async def get_all_open_tickets() -> List[dict]:
    """Получить все открытые тикеты"""
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT id, user_id, username, status, created_at FROM tickets WHERE status = 'open' ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [{"id": r[0], "user_id": r[1], "username": r[2], "status": r[3], "created_at": r[4]} for r in rows]


async def close_ticket(ticket_id: int):
    """Закрыть тикет"""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("UPDATE tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
        await db.commit()


async def add_ticket_message(ticket_id: int, sender_type: str, message: str):
    """Добавить сообщение в тикет (sender_type: 'user' или 'admin')"""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT INTO ticket_messages (ticket_id, sender_type, message) VALUES (?, ?, ?)",
            (ticket_id, sender_type, message)
        )
        await db.commit()


async def get_ticket_messages(ticket_id: int) -> List[dict]:
    """Получить сообщения тикета"""
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT id, sender_type, message, created_at FROM ticket_messages WHERE ticket_id = ? ORDER BY created_at",
            (ticket_id,)
        )
        rows = await cursor.fetchall()
        return [{"id": r[0], "sender_type": r[1], "message": r[2], "created_at": r[3]} for r in rows]
