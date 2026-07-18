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
    db.commit()
