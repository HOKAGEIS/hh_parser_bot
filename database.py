# database.py (FIXED)
from __future__ import annotations

import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from contextlib import asynccontextmanager

import aiosqlite

try:
    from config import config  # optional
except Exception:
    config = None


DATABASE = getattr(config, "DB_PATH", None) or getattr(config, "DATABASE", None) or "hh_bot.db"


# ==================== DATACLASSES ====================

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

    # HH tokens (чтобы не падал ваш search_router)
    hh_access_token: Optional[str]
    hh_refresh_token: Optional[str]
    hh_token_expires_at: Optional[str]

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
    exclude_words: Optional[str]   # json-string (как у вас было)
    last_vacancy_id: Optional[str]
    last_check: Optional[str]
    active: bool
    created_at: str

    @property
    def exclude_words_list(self) -> List[str]:
        try:
            return json.loads(self.exclude_words or "[]")
        except Exception:
            return []


# ==================== HELPERS ====================

def _now_iso() -> str:
    return datetime.now().isoformat()


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _json_loads(s: Optional[str], default: Any):
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception:
        return default


@asynccontextmanager
async def _db() -> aiosqlite.Connection:
    """
    Правильный способ для aiosqlite:
    - НЕ делать: async with await aiosqlite.connect(...)
    - Делаем: async with aiosqlite.connect(...) as db
    """
    async with aiosqlite.connect(DATABASE) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("PRAGMA journal_mode = WAL;")
        yield db


async def _ensure_columns(db: aiosqlite.Connection, table: str, columns: Dict[str, str]) -> None:
    cur = await db.execute(f"PRAGMA table_info({table})")
    rows = await cur.fetchall()
    existing = {r["name"] for r in rows}

    for col, sql_def in columns.items():
        if col not in existing:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {sql_def}")


# ==================== INIT ====================

async def init_db():
    """Инициализация базы данных + мягкие миграции."""
    async with _db() as db:
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

        # Миграция: HH токены (чтобы search_router не падал)
        await _ensure_columns(db, "users", {
            "hh_access_token": "TEXT",
            "hh_refresh_token": "TEXT",
            "hh_token_expires_at": "TEXT",
        })

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

        # Отправленные уведомления
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

        # applied (нужно для was_applied/mark_applied)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS applied (
                user_id INTEGER NOT NULL,
                vacancy_id TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, vacancy_id)
            )
        """)

        # Индексы
        await db.execute("CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(active)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_history_user ON search_history(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_applied_user ON applied(user_id)")

        await db.commit()

    print("✅ База данных инициализирована")


# ==================== USERS ====================

async def create_user(user_id: int, username: str = None):
    async with _db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (id, username, exclude_words) VALUES (?, ?, '[]')",
            (user_id, username),
        )
        if username:
            await db.execute("UPDATE users SET username = COALESCE(?, username) WHERE id = ?", (username, user_id))
        await db.commit()


async def ensure_user(user_id: int, username: str = None):
    await create_user(user_id, username=username)


async def get_user(user_id: int) -> Optional[User]:
    async with _db() as db:
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        if not row:
            return None

        # на старых БД до миграции ключей может не быть -> страхуемся
        keys = set(row.keys())

        return User(
            id=int(row["id"]),
            username=row["username"],
            default_city=row["default_city"],
            default_city_name=row["default_city_name"],
            default_experience=row["default_experience"],
            default_schedule=row["default_schedule"],
            min_salary=row["min_salary"],
            only_with_salary=bool(row["only_with_salary"]),
            exclude_words=_json_loads(row["exclude_words"], []),
            notifications_enabled=bool(row["notifications_enabled"]),
            hh_access_token=row["hh_access_token"] if "hh_access_token" in keys else None,
            hh_refresh_token=row["hh_refresh_token"] if "hh_refresh_token" in keys else None,
            hh_token_expires_at=row["hh_token_expires_at"] if "hh_token_expires_at" in keys else None,
            created_at=row["created_at"] or "",
        )


async def update_user_settings(user_id: int, **kwargs):
    async with _db() as db:
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
            # HH tokens
            "hh_access_token": "hh_access_token",
            "hh_refresh_token": "hh_refresh_token",
            "hh_token_expires_at": "hh_token_expires_at",
        }

        for key, value in kwargs.items():
            if key not in field_map:
                continue

            col = field_map[key]

            if key == "exclude_words":
                if isinstance(value, list):
                    value = _json_dumps([w.strip().lower() for w in value if w and w.strip()])
                elif value is None:
                    value = "[]"

            if key in ("only_with_salary", "notifications_enabled") and value is not None:
                value = 1 if bool(value) else 0

            updates.append(f"{col} = ?")
            values.append(value)

        if updates:
            values.append(user_id)
            await db.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", values)
            await db.commit()


async def set_user_exclude_words(user_id: int, words: List[str]):
    await ensure_user(user_id)
    words_norm = [w.strip().lower() for w in (words or []) if w and w.strip()]
    await update_user_settings(user_id, exclude_words=words_norm)


async def get_all_users_with_notifications() -> List[int]:
    async with _db() as db:
        cursor = await db.execute("SELECT id FROM users WHERE notifications_enabled = 1")
        rows = await cursor.fetchall()
        return [int(r["id"]) for r in rows]


# ==================== SEARCH HISTORY ====================

async def add_search_history(user_id: int, query: str, city: str = None, city_name: str = None, filters: dict = None):
    async with _db() as db:
        await db.execute("DELETE FROM search_history WHERE user_id = ? AND query = ?", (user_id, query))
        await db.execute(
            "INSERT INTO search_history (user_id, query, city, city_name, filters) VALUES (?, ?, ?, ?, ?)",
            (user_id, query, city, city_name, _json_dumps(filters or {})),
        )
        await db.execute("""
            DELETE FROM search_history WHERE user_id = ? AND id NOT IN (
                SELECT id FROM search_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 10
            )
        """, (user_id, user_id))
        await db.commit()


async def get_search_history(user_id: int, limit: int = 10) -> List[dict]:
    async with _db() as db:
        cursor = await db.execute(
            "SELECT query, city, city_name, filters, created_at FROM search_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "query": r["query"],
                "city": r["city"],
                "city_name": r["city_name"],
                "filters": _json_loads(r["filters"], {}),
                "created_at": r["created_at"],
            }
            for r in rows
        ]


async def clear_search_history(user_id: int):
    async with _db() as db:
        await db.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
        await db.commit()


# ==================== FAVORITES ====================

async def add_favorite(user_id: int, vacancy_id: str, vacancy_data: dict):
    async with _db() as db:
        try:
            await db.execute(
                "INSERT INTO favorites (user_id, vacancy_id, vacancy_data) VALUES (?, ?, ?)",
                (user_id, vacancy_id, _json_dumps(vacancy_data or {})),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def remove_favorite(user_id: int, vacancy_id: str):
    async with _db() as db:
        await db.execute("DELETE FROM favorites WHERE user_id = ? AND vacancy_id = ?", (user_id, vacancy_id))
        await db.commit()


async def get_favorites(user_id: int) -> List[Favorite]:
    async with _db() as db:
        cursor = await db.execute(
            "SELECT id, user_id, vacancy_id, vacancy_data, added_at FROM favorites WHERE user_id = ? ORDER BY added_at DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [
            Favorite(
                id=int(r["id"]),
                user_id=int(r["user_id"]),
                vacancy_id=r["vacancy_id"],
                vacancy_data=_json_loads(r["vacancy_data"], {}),
                added_at=r["added_at"],
            )
            for r in rows
        ]


async def is_favorite(user_id: int, vacancy_id: str) -> bool:
    async with _db() as db:
        cursor = await db.execute("SELECT 1 FROM favorites WHERE user_id = ? AND vacancy_id = ?", (user_id, vacancy_id))
        return await cursor.fetchone() is not None


async def clear_favorites(user_id: int):
    async with _db() as db:
        await db.execute("DELETE FROM favorites WHERE user_id = ?", (user_id,))
        await db.commit()


# Совместимость с моим новым названием
async def list_favorites(user_id: int) -> List[Favorite]:
    return await get_favorites(user_id)


# ==================== APPLIED (отклики) ====================

async def mark_applied(user_id: int, vacancy_id: str):
    async with _db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO applied (user_id, vacancy_id, applied_at) VALUES (?, ?, ?)",
            (user_id, vacancy_id, _now_iso()),
        )
        await db.commit()


async def was_applied(user_id: int, vacancy_id: str) -> bool:
    async with _db() as db:
        cur = await db.execute("SELECT 1 FROM applied WHERE user_id = ? AND vacancy_id = ?", (user_id, vacancy_id))
        return await cur.fetchone() is not None


# ==================== SUBSCRIPTIONS ====================

async def add_subscription(
    user_id: int,
    query: str,
    city: str = None,
    city_name: str = None,
    experience: str = None,
    schedule: str = None,
    min_salary: int = None,
    exclude_words: List[str] = None,
) -> int:
    async with _db() as db:
        cursor = await db.execute(
            """INSERT INTO subscriptions
               (user_id, query, city, city_name, experience, schedule, min_salary, exclude_words)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, query, city, city_name, experience, schedule, min_salary, _json_dumps(exclude_words or [])),
        )
        await db.commit()
        return int(cursor.lastrowid)


async def get_subscriptions(user_id: int, active_only: bool = True) -> List[Subscription]:
    async with _db() as db:
        sql = "SELECT * FROM subscriptions WHERE user_id = ?"
        if active_only:
            sql += " AND active = 1"
        cursor = await db.execute(sql, (user_id,))
        rows = await cursor.fetchall()

        result: List[Subscription] = []
        for r in rows:
            result.append(Subscription(
                id=int(r["id"]),
                user_id=int(r["user_id"]),
                query=r["query"],
                city=r["city"],
                city_name=r["city_name"],
                experience=r["experience"],
                schedule=r["schedule"],
                min_salary=r["min_salary"],
                exclude_words=r["exclude_words"],
                last_vacancy_id=r["last_vacancy_id"],
                last_check=r["last_check"],
                active=bool(r["active"]),
                created_at=r["created_at"],
            ))
        return result


async def get_all_active_subscriptions() -> List[Subscription]:
    async with _db() as db:
        cursor = await db.execute("SELECT * FROM subscriptions WHERE active = 1")
        rows = await cursor.fetchall()

        result: List[Subscription] = []
        for r in rows:
            result.append(Subscription(
                id=int(r["id"]),
                user_id=int(r["user_id"]),
                query=r["query"],
                city=r["city"],
                city_name=r["city_name"],
                experience=r["experience"],
                schedule=r["schedule"],
                min_salary=r["min_salary"],
                exclude_words=r["exclude_words"],
                last_vacancy_id=r["last_vacancy_id"],
                last_check=r["last_check"],
                active=bool(r["active"]),
                created_at=r["created_at"],
            ))
        return result


async def get_subscriptions_count(user_id: int) -> int:
    async with _db() as db:
        cursor = await db.execute("SELECT COUNT(*) AS c FROM subscriptions WHERE user_id = ? AND active = 1", (user_id,))
        row = await cursor.fetchone()
        return int(row["c"]) if row else 0


async def delete_subscription(sub_id: int, user_id: Optional[int] = None):
    async with _db() as db:
        if user_id is None:
            await db.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,))
        else:
            await db.execute("DELETE FROM subscriptions WHERE id = ? AND user_id = ?", (sub_id, user_id))
        await db.commit()


async def toggle_subscription(sub_id: int, user_id: int) -> bool:
    async with _db() as db:
        cursor = await db.execute("SELECT active FROM subscriptions WHERE id = ? AND user_id = ?", (sub_id, user_id))
        row = await cursor.fetchone()
        if not row:
            return False

        new_status = 0 if bool(row["active"]) else 1
        await db.execute("UPDATE subscriptions SET active = ? WHERE id = ?", (new_status, sub_id))
        await db.commit()
        return bool(new_status)


async def set_subscription_active(sub_id: int, active: bool):
    async with _db() as db:
        await db.execute("UPDATE subscriptions SET active = ? WHERE id = ?", (1 if active else 0, sub_id))
        await db.commit()


async def update_subscription_last_check(sub_id: int, last_vacancy_id: str = None):
    async with _db() as db:
        if last_vacancy_id:
            await db.execute(
                "UPDATE subscriptions SET last_check = ?, last_vacancy_id = ? WHERE id = ?",
                (_now_iso(), last_vacancy_id, sub_id),
            )
        else:
            await db.execute(
                "UPDATE subscriptions SET last_check = ? WHERE id = ?",
                (_now_iso(), sub_id),
            )
        await db.commit()


# Alias-ы под другой стиль имен (если где-то использовали)
async def get_active_subscriptions() -> List[Subscription]:
    return await get_all_active_subscriptions()


async def touch_subscription_checked(sub_id: int):
    await update_subscription_last_check(sub_id)


# ==================== NOTIFICATIONS ====================

async def was_notification_sent(user_id: int, subscription_id: int, vacancy_id: str) -> bool:
    async with _db() as db:
        cursor = await db.execute(
            "SELECT 1 FROM sent_notifications WHERE user_id = ? AND subscription_id = ? AND vacancy_id = ?",
            (user_id, subscription_id, vacancy_id),
        )
        return await cursor.fetchone() is not None


async def mark_notification_sent(user_id: int, subscription_id: int, vacancy_id: str):
    async with _db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO sent_notifications (user_id, subscription_id, vacancy_id) VALUES (?, ?, ?)",
            (user_id, subscription_id, vacancy_id),
        )
        await db.commit()


async def cleanup_old_notifications(days: int = 7):
    async with _db() as db:
        await db.execute(
            "DELETE FROM sent_notifications WHERE sent_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        await db.commit()


# ==================== SUPPORT TICKETS ====================

async def create_ticket(user_id: int, username: str = None) -> int:
    async with _db() as db:
        cursor = await db.execute("INSERT INTO tickets (user_id, username) VALUES (?, ?)", (user_id, username))
        await db.commit()
        return int(cursor.lastrowid)


async def get_open_ticket(user_id: int) -> Optional[dict]:
    async with _db() as db:
        cursor = await db.execute(
            "SELECT id, user_id, username, status, created_at FROM tickets WHERE user_id = ? AND status = 'open'",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row:
            return {"id": int(row["id"]), "user_id": int(row["user_id"]), "username": row["username"], "status": row["status"], "created_at": row["created_at"]}
    return None


async def get_ticket_by_id(ticket_id: int) -> Optional[dict]:
    async with _db() as db:
        cursor = await db.execute(
            "SELECT id, user_id, username, status, created_at FROM tickets WHERE id = ?",
            (ticket_id,),
        )
        row = await cursor.fetchone()
        if row:
            return {"id": int(row["id"]), "user_id": int(row["user_id"]), "username": row["username"], "status": row["status"], "created_at": row["created_at"]}
    return None


async def get_all_open_tickets() -> List[dict]:
    async with _db() as db:
        cursor = await db.execute(
            "SELECT id, user_id, username, status, created_at FROM tickets WHERE status = 'open' ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [{"id": int(r["id"]), "user_id": int(r["user_id"]), "username": r["username"], "status": r["status"], "created_at": r["created_at"]} for r in rows]


async def close_ticket(ticket_id: int):
    async with _db() as db:
        await db.execute("UPDATE tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
        await db.commit()


async def add_ticket_message(ticket_id: int, sender_type: str, message: str):
    async with _db() as db:
        await db.execute(
            "INSERT INTO ticket_messages (ticket_id, sender_type, message) VALUES (?, ?, ?)",
            (ticket_id, sender_type, message),
        )
        await db.commit()


async def get_ticket_messages(ticket_id: int) -> List[dict]:
    async with _db() as db:
        cursor = await db.execute(
            "SELECT id, sender_type, message, created_at FROM ticket_messages WHERE ticket_id = ? ORDER BY created_at",
            (ticket_id,),
        )
        rows = await cursor.fetchall()
        return [{"id": int(r["id"]), "sender_type": r["sender_type"], "message": r["message"], "created_at": r["created_at"]} for r in rows]
