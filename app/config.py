# .env 값을 읽어 Flask, SQLite, NAS 감시 경로 설정을 관리
import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    HOST = os.getenv("FLASK_HOST", "127.0.0.1").strip()
    PORT = int(os.getenv("FLASK_PORT", "5000"))
    DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "instance/events.sqlite3"))
    NAS_MONITOR_PATH = os.getenv("NAS_MONITOR_PATH", "instance/nas_monitor_files").strip()
    NAS_ALLOW_MAPPED_DRIVE = os.getenv("NAS_ALLOW_MAPPED_DRIVE", "true").lower() == "true"
    LOGIN_MAX_FAILED_ATTEMPTS = int(os.getenv("LOGIN_MAX_FAILED_ATTEMPTS", "3"))
    LOGIN_BLOCK_MINUTES = int(os.getenv("LOGIN_BLOCK_MINUTES", "10"))
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip()
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin1234")

    if not DATABASE_PATH.is_absolute():
        DATABASE_PATH = BASE_DIR / DATABASE_PATH

    if NAS_MONITOR_PATH and not Path(NAS_MONITOR_PATH).is_absolute():
        NAS_MONITOR_PATH = str(BASE_DIR / NAS_MONITOR_PATH)
