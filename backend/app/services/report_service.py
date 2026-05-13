from app.database import get_connection
from app.services.cache import cache
from app.config import CACHE_TTL


def get_stock_reports(code: str, page: int = 1, size: int = 20) -> list[dict]:
    cache_key = f"report:{code}:{page}:{size}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    conn = get_connection()
    offset = (page - 1) * size
    rows = conn.execute(
        "SELECT * FROM reports WHERE code=? ORDER BY publish_date DESC LIMIT ? OFFSET ?",
        (code, size, offset),
    ).fetchall()

    if rows:
        result = [dict(row) for row in rows]
        cache.set(cache_key, result, CACHE_TTL["report"])
        return result

    try:
        from app.datasources.eastmoney_source import fetch_reports
        data = fetch_reports(code, size)
        if data:
            cache.set(cache_key, data, CACHE_TTL["report"])
        return data or []
    except Exception:
        return []


def search_reports(query: str, size: int = 50) -> list[dict]:
    try:
        from app.datasources.iwencai_source import search_reports as iwencai_search
        return iwencai_search(query, size)
    except Exception:
        return []
