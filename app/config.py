# app/config.py — Central configuration for the Text-to-SQL Assistant.
# All paths, API keys, and model names live here — import from this module, never hardcode.

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project root is two levels up from this file (app/config.py → app/ → project root)
BASE_DIR  = Path(__file__).resolve().parent.parent
DATA_DIR  = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_FILENAME   = "ecommerce.db"
DB_PATH       = DATA_DIR / DB_FILENAME
DB_URL        = f"sqlite:///{DB_PATH}"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL   = "gemini-2.5-flash"
GEMINI_TEMP    = 0.0

API_HOST = "0.0.0.0"
API_PORT = 8000
API_BASE = f"http://localhost:{API_PORT}"

MAX_ROWS_RETURNED = 500
SAMPLE_ROWS       = 3

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}

SUPPORTED_DIALECTS = [
    "SQLite", "MySQL", "PostgreSQL", "SQL Server", "Oracle", "BigQuery", "Snowflake",
]
