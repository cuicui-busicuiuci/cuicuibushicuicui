from app.services.cache import cache
from app.config import CACHE_TTL
from app.database import get_connection


def get_stock_quote(code: str, force_realtime: bool = False) -> dict | None:
    cache_key = f"quote:{code}"

    if not force_realtime:
        cached = cache.get(cache_key)
        if cached:
            return cached

    try:
        from app.datasources.tencent_source import fetch_tencent_quote
        data = fetch_tencent_quote(code)
        if data:
            cache.set(cache_key, data, CACHE_TTL["quote"])
            _save_quote_to_db(code, data)
        return data
    except Exception as e:
        conn = get_connection()
        row = conn.execute("SELECT * FROM quotes WHERE code=?", (code,)).fetchone()
        return dict(row) if row else None


def get_batch_quotes(codes: list[str]) -> list[dict]:
    results = []
    for code in codes:
        quote = get_stock_quote(code)
        if quote:
            results.append(quote)
    return results


def get_kline(code: str, category: int = 4, limit: int = 100) -> list[dict]:
    cache_key = f"kline:{code}:{category}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        from app.datasources.mootdx_source import fetch_kline
        data = fetch_kline(code, category, limit)
        if data:
            cache.set(cache_key, data, CACHE_TTL["kline"])
        return data or []
    except Exception as e:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM klines WHERE code=? AND category=? ORDER BY datetime DESC LIMIT ?",
            (code, category, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def _save_quote_to_db(code: str, data: dict):
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO quotes
        (code, name, price, open, high, low, last_close, change_amt, change_pct,
         volume, amount, turnover_pct, pe_ttm, pb, mcap_yi, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (
            code, data.get("name"), data.get("price"), data.get("open"),
            data.get("high"), data.get("low"), data.get("last_close"),
            data.get("change_amt"), data.get("change_pct"),
            data.get("volume"), data.get("amount"), data.get("turnover_pct"),
            data.get("pe_ttm"), data.get("pb"), data.get("mcap_yi"),
        ),
    )
