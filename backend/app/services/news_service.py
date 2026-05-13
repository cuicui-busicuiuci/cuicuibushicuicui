from app.database import get_connection


def get_stock_news(code: str, page: int = 1, size: int = 20) -> list[dict]:
    conn = get_connection()
    offset = (page - 1) * size
    rows = conn.execute(
        "SELECT * FROM news WHERE code=? ORDER BY pub_time DESC LIMIT ? OFFSET ?",
        (code, size, offset),
    ).fetchall()

    if rows:
        return [dict(row) for row in rows]

    try:
        from app.datasources.akshare_source import fetch_stock_news
        data = fetch_stock_news(code)
        return data[:size] if data else []
    except Exception:
        return []


def get_cls_flash(limit: int = 50) -> list[dict]:
    try:
        from app.datasources.akshare_source import fetch_cls_news
        data = fetch_cls_news(limit)
        return data or []
    except Exception:
        return []


def get_global_news(limit: int = 50) -> list[dict]:
    try:
        from app.datasources.akshare_source import fetch_global_news
        data = fetch_global_news(limit)
        return data or []
    except Exception:
        return []
