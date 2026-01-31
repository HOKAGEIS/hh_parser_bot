import sqlite3
import json
from datetime import datetime
from typing import List, Tuple, Optional
import os
from config import Config

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица вакансий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vacancies (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            url TEXT NOT NULL,
            description TEXT,
            requirements TEXT,
            salary_min INTEGER,
            salary_max INTEGER,
            currency TEXT,
            area TEXT,
            experience TEXT,
            schedule TEXT,
            employment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица избранных вакансий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER,
            vacancy_id TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, vacancy_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (vacancy_id) REFERENCES vacancies (id)
        )
    ''')
    
    # Таблица истории поиска
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT NOT NULL,
            timestamp REAL,
            filters TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Таблица подписок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT NOT NULL,
            filters TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_user(user_id: int):
    """Добавление пользователя в базу данных"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('INSERT OR IGNORE INTO users (id) VALUES (?)', (user_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def save_vacancy(vacancy_data: dict):
    """Сохранение вакансии в базу данных"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO vacancies 
            (id, title, company, url, description, requirements, 
             salary_min, salary_max, currency, area, experience, schedule, employment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            vacancy_data['id'],
            vacancy_data['title'],
            vacancy_data['company'],
            vacancy_data['url'],
            vacancy_data.get('description', ''),
            vacancy_data.get('requirements', ''),
            vacancy_data.get('salary_min'),
            vacancy_data.get('salary_max'),
            vacancy_data.get('currency', ''),
            vacancy_data.get('area', ''),
            vacancy_data.get('experience', ''),
            vacancy_data.get('schedule', ''),
            vacancy_data.get('employment', '')
        ))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def add_favorite(user_id: int, vacancy_id: str, title: str, company: str, url: str):
    """Добавление вакансии в избранное"""
    # Сначала сохраняем вакансию в таблицу вакансий
    save_vacancy({
        'id': vacancy_id,
        'title': title,
        'company': company,
        'url': url
    })
    
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO favorites (user_id, vacancy_id)
            VALUES (?, ?)
        ''', (user_id, vacancy_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def remove_favorite(user_id: int, vacancy_id: str):
    """Удаление вакансии из избранного"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            DELETE FROM favorites
            WHERE user_id = ? AND vacancy_id = ?
        ''', (user_id, vacancy_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def is_favorite(user_id: int, vacancy_id: str) -> bool:
    """Проверка, является ли вакансия избранной"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT 1 FROM favorites
            WHERE user_id = ? AND vacancy_id = ?
        ''', (user_id, vacancy_id))
        result = cursor.fetchone()
        return result is not None
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()

def get_favorites(user_id: int) -> List[Tuple]:
    """Получение списка избранных вакансий"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT v.id, v.title, v.company, v.url
            FROM favorites f
            JOIN vacancies v ON f.vacancy_id = v.id
            WHERE f.user_id = ?
        ''', (user_id,))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        conn.close()

def add_search_history(user_id: int, query: str, filters: str):
    """Добавление записи в историю поиска"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO search_history (user_id, query, timestamp, filters)
            VALUES (?, ?, ?, ?)
        ''', (user_id, query, datetime.now().timestamp(), filters))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def get_search_history(user_id: int) -> List[Tuple]:
    """Получение истории поиска"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, query, timestamp, filters
            FROM search_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
        ''', (user_id,))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        conn.close()

def add_subscription(user_id: int, query: str, filters: str):
    """Добавление подписки"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO subscriptions (user_id, query, filters)
            VALUES (?, ?, ?)
        ''', (user_id, query, filters))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()
    return True

def remove_subscription(user_id: int, query: str):
    """Удаление подписки"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE subscriptions
            SET is_active = FALSE
            WHERE user_id = ? AND query = ? AND is_active = TRUE
        ''', (user_id, query))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def get_subscriptions(user_id: int) -> List[Tuple]:
    """Получение активных подписок"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, query, filters
            FROM subscriptions
            WHERE user_id = ? AND is_active = TRUE
        ''', (user_id,))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        conn.close()

def get_all_subscriptions() -> List[Tuple]:
    """Получение всех активных подписок (для рассылки)"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT s.user_id, s.query, s.filters
            FROM subscriptions s
            WHERE s.is_active = TRUE
        ''')
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        conn.close()
