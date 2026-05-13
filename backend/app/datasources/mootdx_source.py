import pandas as pd

_client = None


def _get_client():
    global _client
    if _client is None:
        from mootdx.quotes import Quotes
        _client = Quotes.factory(market="std")
    return _client


def fetch_kline(code: str, category: int = 4, limit: int = 100) -> list[dict]:
    client = _get_client()
    market = 1 if code.startswith(("6", "9")) else 0

    df = client.bars(category=category, market=market, symbol=code, offset=limit)

    if df is None or df.empty:
        return []

    result = []
    for _, row in df.iterrows():
        result.append({
            "code": code,
            "category": category,
            "datetime": str(row.get("datetime", "")),
            "open": float(row.get("open", 0)),
            "close": float(row.get("close", 0)),
            "high": float(row.get("high", 0)),
            "low": float(row.get("low", 0)),
            "volume": float(row.get("vol", 0)),
            "amount": float(row.get("amount", 0)),
        })
    return result


def fetch_realtime_quote(code: str) -> dict | None:
    client = _get_client()
    market = 1 if code.startswith(("6", "9")) else 0

    df = client.quotes(market=market, symbol=code)

    if df is None or df.empty:
        return None

    row = df.iloc[0]
    return {
        "code": code,
        "price": float(row.get("price", 0)),
        "open": float(row.get("open", 0)),
        "high": float(row.get("high", 0)),
        "low": float(row.get("low", 0)),
        "last_close": float(row.get("last_close", 0)),
        "volume": float(row.get("vol", 0)),
        "amount": float(row.get("amount", 0)),
    }


def fetch_finance(code: str) -> dict | None:
    client = _get_client()
    market = 1 if code.startswith(("6", "9")) else 0

    df = client.finance(symbol=code, market=market)

    if df is None or df.empty:
        return None

    row = df.iloc[0]
    return {
        "code": code,
        "eps": float(row.get("eps", 0)),
        "bvps": float(row.get("bvps", 0)),
        "total_share": float(row.get("total_share", 0)),
        "float_share": float(row.get("float_share", 0)),
    }
