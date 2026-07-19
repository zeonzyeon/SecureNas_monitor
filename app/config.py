# .env 값을 읽어 Flask, SQLite, NAS 감시 경로 설정을 관리
import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "instance/events.sqlite3"))
    NAS_MONITOR_PATH = os.getenv("NAS_MONITOR_PATH", "").strip()
    NAS_ALLOW_MAPPED_DRIVE = os.getenv("NAS_ALLOW_MAPPED_DRIVE", "false").lower() == "true"
    LOGIN_MAX_FAILED_ATTEMPTS = int(os.getenv("LOGIN_MAX_FAILED_ATTEMPTS", "3"))
    LOGIN_BLOCK_MINUTES = int(os.getenv("LOGIN_BLOCK_MINUTES", "10"))
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip()
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin1234")

    if not DATABASE_PATH.is_absolute():
        DATABASE_PATH = BASE_DIR / DATABASE_PATH
