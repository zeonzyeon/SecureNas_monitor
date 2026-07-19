# SQLite 연결을 관리하고 파일 이벤트 저장 테이블을 초기화
import sqlite3
from pathlib import Path

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS file_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    src_path TEXT,
    dest_path TEXT,
    is_directory INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'watchdog',
    user_name TEXT,
    ip_address TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_file_events_created_at
ON file_events (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_file_events_event_type
ON file_events (event_type);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (role IN ('admin', 'user', 'viewer'))
);

CREATE INDEX IF NOT EXISTS idx_users_username
ON users (username);

CREATE INDEX IF NOT EXISTS idx_users_role
ON users (role);

CREATE TABLE IF NOT EXISTS login_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL DEFAULT 'login_attempt',
    username TEXT NOT NULL,
    user_id INTEGER,
    success INTEGER NOT NULL DEFAULT 0,
    ip_address TEXT,
    user_agent TEXT,
    message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS idx_login_logs_created_at
ON login_logs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_login_logs_user_id
ON login_logs (user_id);

CREATE TABLE IF NOT EXISTS ip_blocks (
    ip_address TEXT PRIMARY KEY,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    last_failed_at TEXT,
    blocked_at TEXT,
    blocked_until TEXT,
    is_blocked INTEGER NOT NULL DEFAULT 0,
    blocked_by TEXT,
    block_reason TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ip_blocks_is_blocked
ON ip_blocks (is_blocked);

CREATE INDEX IF NOT EXISTS idx_ip_blocks_blocked_until
ON ip_blocks (blocked_until);

CREATE TABLE IF NOT EXISTS download_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    ip_address TEXT,
    success INTEGER NOT NULL DEFAULT 0,
    message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS idx_download_logs_created_at
ON download_logs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_download_logs_user_id
ON download_logs (user_id);
"""


def get_db():
    if "db" not in g:
        database_path = Path(current_app.config["DATABASE_PATH"])
        database_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(database_path)
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(error=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    _ensure_column(db, "login_logs", "event_type", "TEXT NOT NULL DEFAULT 'login_attempt'")
    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_login_logs_event_type
        ON login_logs (event_type)
        """
    )
    db.commit()


def _ensure_column(db, table_name, column_name, column_definition):
    columns = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    if any(column["name"] == column_name for column in columns):
        return

    db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
