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
    default_experience: Optional[str]
    default_schedule: Optional[str]
    min_salary: Optional[int]
    only_with_salary: bool
    created_at: str

@dataclass
class Favorite:
    id: int
    user_id: int
    vacancy_id: str
    vacancy_data: dict  # JSON с данными вакансии
    added_at: str

@dataclass
class Subscription:
    id: int
    user_id: int
    query: str
    city: Optional[str]
    experience: Optional[str]
    schedule: Optional[str]
    min_salary: Optional[int]
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
                default_experience TEXT,
                default_schedule TEXT,
                min_salary INTEGER,
                only_with_salary BOOLEAN DEFAULT 0,
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
                experience TEXT,
                schedule TEXT,
                min_salary INTEGER,
                last_vacancy_id TEXT,
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # История поиска
        await db.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                query TEXT NOT NULL,
                results_count INTEGER,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
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
            return User(*row)
    return None

async def create_user(user_id: int, username: str = None):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            """INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)""",
            (user_id, username)
        )
        await db.commit()

async def update_user_settings(
    user_id: int,
    city: str = None,
    experience: str = None,
    schedule: str = None,
    min_salary: int = None,
    only_with_salary: bool = None
):
    async with aiosqlite.connect(DATABASE) as db:
        updates = []
        values = []
        
        if city is not None:
            updates.append("default_city = ?")
            values.append(city)
        if experience is not None:
            updates.append("default_experience = ?")
            values.append(experience)
        if schedule is not None:
            updates.append("default_schedule = ?")
            values.append(schedule)
        if min_salary is not None:
            updates.append("min_salary = ?")
            values.append(min_salary)
        if only_with_salary is not None:
            updates.append("only_with_salary = ?")
            values.append(only_with_salary)
        
        if updates:
            values.append(user_id)
            await db.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
                values
            )
            await db.commit()


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
            return False  # Уже в избранном

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

async def get_favorites_count(user_id: int) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM favorites WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


# ==================== ПОДПИСКИ ====================

async def add_subscription(
    user_id: int,
    query: str,
    city: str = None,
    experience: str = None,
    schedule: str = None,
    min_salary: int = None
) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            """INSERT INTO subscriptions 
               (user_id, query, city, experience, schedule, min_salary)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, query, city, experience, schedule, min_salary)
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

async def get_all_active_subscriptions() -> List[Subscription]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT * FROM subscriptions WHERE active = 1"
        )
        rows = await cursor.fetchall()
        return [Subscription(*row) for row in rows]

async def update_subscription_last_vacancy(sub_id: int, vacancy_id: str):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "UPDATE subscriptions SET last_vacancy_id = ? WHERE id = ?",
            (vacancy_id, sub_id)
        )
        await db.commit()

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

async def get_subscriptions_count(user_id: int) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM subscriptions WHERE user_id = ? AND active = 1",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


# ==================== ИСТОРИЯ ====================

async def add_search_history(user_id: int, query: str, results_count: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT INTO search_history (user_id, query, results_count) VALUES (?, ?, ?)",
            (user_id, query, results_count)
        )
        await db.commit()

async def get_popular_queries(user_id: int, limit: int = 5) -> List[str]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            """SELECT query, COUNT(*) as cnt FROM search_history 
               WHERE user_id = ? GROUP BY query ORDER BY cnt DESC LIMIT ?""",
            (user_id, limit)
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
