import sqlite3
from contextlib import contextmanager

DB_PATH = "bot.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            room TEXT,
            date TEXT,
            status TEXT DEFAULT 'active'
        )
        """)
        conn.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def add_request(user_id, username, room, date):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO requests (user_id, username, room, date) VALUES (?, ?, ?, ?)",
                    (user_id, username, room, date))
        conn.commit()

def list_requests(user_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, room, date, status FROM requests WHERE user_id=? ORDER BY date DESC", (user_id,))
        return cur.fetchall()

def cancel_request(request_id, user_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE requests SET status='cancelled' WHERE id=? AND user_id=?", (request_id, user_id))
        conn.commit()
        return cur.rowcount