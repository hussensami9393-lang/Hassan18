# ==========================================
#   قاعدة البيانات - database.py
# ==========================================

import sqlite3
import json
from datetime import datetime
from config import DATABASE_PATH


def get_connection():
    """الاتصال بقاعدة البيانات"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """إنشاء الجداول عند أول تشغيل"""
    conn = get_connection()
    cursor = conn.cursor()

    # جدول المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id       INTEGER PRIMARY KEY,
            username      TEXT,
            full_name     TEXT,
            ton_wallet    TEXT DEFAULT NULL,
            stars_balance INTEGER DEFAULT 0,
            ton_balance   REAL DEFAULT 0.0,
            total_sold    INTEGER DEFAULT 0,
            total_bought  INTEGER DEFAULT 0,
            total_earned  REAL DEFAULT 0.0,
            is_banned     INTEGER DEFAULT 0,
            joined_at     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # جدول طلبات البيع (بيع نجوم مقابل TON)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sell_orders (
            order_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER,
            stars_amount  INTEGER,
            ton_amount    REAL,
            commission    REAL,
            net_ton       REAL,
            ton_wallet    TEXT,
            status        TEXT DEFAULT 'pending',
            tx_hash       TEXT DEFAULT NULL,
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at    TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    # جدول طلبات الشراء (شراء نجوم بـ TON)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buy_orders (
            order_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER,
            stars_amount  INTEGER,
            ton_amount    REAL,
            commission    REAL,
            status        TEXT DEFAULT 'pending',
            payment_id    TEXT DEFAULT NULL,
            tx_hash       TEXT DEFAULT NULL,
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at    TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    # جدول التحويلات المباشرة (TON لشخص آخر)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transfers (
            transfer_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id  INTEGER,
            to_user_id    INTEGER,
            ton_amount    REAL,
            stars_amount  INTEGER DEFAULT 0,
            transfer_type TEXT,
            tx_hash       TEXT DEFAULT NULL,
            status        TEXT DEFAULT 'pending',
            note          TEXT DEFAULT NULL,
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_user_id) REFERENCES users(user_id),
            FOREIGN KEY (to_user_id)   REFERENCES users(user_id)
        )
    ''')

    # جدول إعدادات البوت
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key_name      TEXT PRIMARY KEY,
            value         TEXT,
            updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # جدول السجلات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            log_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER,
            action        TEXT,
            details       TEXT,
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ تم إنشاء قاعدة البيانات بنجاح")


# ========== دوال المستخدمين ==========

def get_or_create_user(user_id: int, username: str = None, full_name: str = None):
    """الحصول على مستخدم أو إنشاؤه"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute(
            "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name)
        )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    conn.close()
    return dict(user)


def update_user_wallet(user_id: int, wallet: str):
    conn = get_connection()
    conn.execute("UPDATE users SET ton_wallet = ? WHERE user_id = ?", (wallet, user_id))
    conn.commit()
    conn.close()


def get_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def ban_user(user_id: int, ban: bool = True):
    conn = get_connection()
    conn.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (1 if ban else 0, user_id))
    conn.commit()
    conn.close()


def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY joined_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ========== دوال طلبات البيع ==========

def create_sell_order(user_id, stars_amount, ton_amount, commission, net_ton, ton_wallet):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sell_orders (user_id, stars_amount, ton_amount, commission, net_ton, ton_wallet)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, stars_amount, ton_amount, commission, net_ton, ton_wallet))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id


def update_sell_order_status(order_id, status, tx_hash=None):
    conn = get_connection()
    conn.execute('''
        UPDATE sell_orders SET status = ?, tx_hash = ?, updated_at = CURRENT_TIMESTAMP
        WHERE order_id = ?
    ''', (status, tx_hash, order_id))
    conn.commit()
    conn.close()


def get_sell_order(order_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sell_orders WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_sell_orders(user_id, limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM sell_orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pending_sell_orders():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sell_orders WHERE status = 'pending' ORDER BY created_at ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ========== دوال طلبات الشراء ==========

def create_buy_order(user_id, stars_amount, ton_amount, commission):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO buy_orders (user_id, stars_amount, ton_amount, commission)
        VALUES (?, ?, ?, ?)
    ''', (user_id, stars_amount, ton_amount, commission))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id


def update_buy_order_status(order_id, status, payment_id=None, tx_hash=None):
    conn = get_connection()
    conn.execute('''
        UPDATE buy_orders SET status = ?, payment_id = ?, tx_hash = ?, updated_at = CURRENT_TIMESTAMP
        WHERE order_id = ?
    ''', (status, payment_id, tx_hash, order_id))
    conn.commit()
    conn.close()


def get_buy_order(order_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM buy_orders WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_pending_buy_orders():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM buy_orders WHERE status = 'pending' ORDER BY created_at ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ========== دوال الإحصائيات ==========

def get_stats():
    conn = get_connection()
    cursor = conn.cursor()
    stats = {}
    cursor.execute("SELECT COUNT(*) as cnt FROM users")
    stats['total_users'] = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE is_banned = 0")
    stats['active_users'] = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt, SUM(stars_amount) as total_stars, SUM(net_ton) as total_ton FROM sell_orders WHERE status = 'completed'")
    row = cursor.fetchone()
    stats['completed_sell_orders'] = row['cnt']
    stats['total_stars_sold']  = row['total_stars'] or 0
    stats['total_ton_paid']    = row['total_ton']   or 0
    cursor.execute("SELECT COUNT(*) as cnt FROM sell_orders WHERE status = 'pending'")
    stats['pending_sell_orders'] = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM buy_orders WHERE status = 'pending'")
    stats['pending_buy_orders']  = cursor.fetchone()['cnt']
    cursor.execute("SELECT SUM(commission) as total FROM sell_orders WHERE status = 'completed'")
    stats['total_commission'] = cursor.fetchone()['total'] or 0
    conn.close()
    return stats


def log_action(user_id, action, details=""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)",
        (user_id, action, details)
    )
    conn.commit()
    conn.close()


# ========== إعدادات البوت ==========

def get_setting(key, default=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key_name = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else default


def set_setting(key, value):
    conn = get_connection()
    conn.execute('''
        INSERT INTO settings (key_name, value) VALUES (?, ?)
        ON CONFLICT(key_name) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
    ''', (key, value, value))
    conn.commit()
    conn.close()
