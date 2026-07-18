import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "instance/events.sqlite3"))
    NAS_MONITOR_PATH = os.getenv("NAS_MONITOR_PATH", "").strip()

    if not DATABASE_PATH.is_absolute():
        DATABASE_PATH = BASE_DIR / DATABASE_PATH
