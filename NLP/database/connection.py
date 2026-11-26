
import sqlite3
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "database" / "hsk_tutor.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS quiz_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                hsk_level INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                score INTEGER NOT NULL,
                percentage REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Thêm user_id cho database đã có từ các phiên bản trước.
        session_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(quiz_sessions)")
        }
        if "user_id" not in session_columns:
            conn.execute(
                "ALTER TABLE quiz_sessions "
                "ADD COLUMN user_id INTEGER REFERENCES users(id)"
            )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user "
            "ON quiz_sessions(user_id, id)"
        )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                question_id TEXT NOT NULL,
                selected_option TEXT,
                correct_option TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                topic TEXT,
                FOREIGN KEY (session_id)
                    REFERENCES quiz_sessions(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hsk_level INTEGER,
                topic TEXT,
                question_text TEXT,
                correct_option TEXT,
                explanation TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS question_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_key TEXT NOT NULL,
                hsk_level INTEGER NOT NULL,
                topic TEXT NOT NULL,
                question_type TEXT,
                question_text TEXT NOT NULL,
                options_json TEXT NOT NULL,
                correct_option TEXT NOT NULL,
                explanation TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (hsk_level, question_key)
            )
        """)
