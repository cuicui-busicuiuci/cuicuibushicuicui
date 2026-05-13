from app.database import get_connection
from app.services.cache import cache
from app.config import CACHE_TTL
from collections import Counter


def get_ths_hot(date: str) -> list[dict]:
    cache_key = f"ths_hot:{date}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        from app.datasources.ths_hot_source import fetch_ths_hot
        data = fetch_ths_hot(date)
        if data:
            cache.set(cache_key, data, CACHE_TTL["ths_hot"])
            _save_ths_hot_to_db(data)
        return data or []
    except Exception:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM ths_hot WHERE date=? ORDER BY change_pct DESC",
            (date,),
        ).fetchall()
        return [dict(row) for row in rows]


def _save_ths_hot_to_db(data: list[dict]):
    conn = get_connection()
    for item in data:
        conn.execute(
            """INSERT OR REPLACE INTO ths_hot
            (date, code, name, reason, change_pct, close_price)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (item["date"], item["code"], item["name"], item["reason"],
             item["change_pct"], item["close_price"]),
        )


def get_hot_topics(date: str, top: int = 10) -> list[dict]:
    hot_stocks = get_ths_hot(date)
    reasons = []
    for stock in hot_stocks:
        reason = stock.get("reason", "")
        if reason:
            tags = [t.strip() for t in reason.replace("，", ",").split(",") if t.strip()]
            reasons.extend(tags)

    counter = Counter(reasons)
    return [{"topic": topic, "count": count} for topic, count in counter.most_common(top)]


def get_north_realtime() -> dict:
    cache_key = "north:realtime"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        from app.datasources.ths_north_source import fetch_north_realtime
        data = fetch_north_realtime()
        if data:
            cache.set(cache_key, data, CACHE_TTL["north"])
        return data or {}
    except Exception:
        return {}


def get_north_history(type: str = "hgt") -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM north_flow WHERE time='daily' ORDER BY date DESC LIMIT 30"
    ).fetchall()
    return [dict(row) for row in rows]
