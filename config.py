# config.py
import os

def _load_env(filepath=".env"):
    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key not in os.environ:
                    os.environ[key] = value
    except FileNotFoundError:
        pass

_load_env()

# Database
DB_PATH = os.environ.get("DB_PATH", "bot.db")

# Google Sheets
SHEETS_CREDENTIALS_FILE = os.environ.get("SHEETS_CREDENTIALS", "credentials.json")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1T1KPo-ZmDQPOHrEB9xs8EVI8klh7EFwPczB9c0d1Ykg")
RANGE_NAME = "Sheet1!A:E"
BATCH_SIZE = 50

# Telegram (polling)
TELEGRAM_TOKEN = os.environ.get("RIOT_TOKEN", "")
TELEGRAM_POLL_INTERVAL = float(os.environ.get("TELEGRAM_POLL_INTERVAL", "2"))

# LLM Fallback
LLM_ENABLED = os.environ.get("LLM_ENABLED", "false").lower() == "true"
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "free")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8402/v1")
LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "30.0"))

# File watcher
FILES_DIR = os.environ.get("FILES_DIR", "files")
