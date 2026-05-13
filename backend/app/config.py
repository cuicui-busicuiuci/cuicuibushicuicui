from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "stock.db"

CACHE_TTL = {
    "quote": 30,
    "kline": 300,
    "report": 1800,
    "valuation": 300,
    "north": 60,
    "ths_hot": 600,
}

CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
