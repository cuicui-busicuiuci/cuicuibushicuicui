from app.services.market_service import get_stock_quote


def full_valuation(code: str) -> dict:
    quote = get_stock_quote(code, force_realtime=True)
    if not quote:
        return {"error": f"无法获取 {code} 的行情数据"}

    price = quote.get("price", 0)
    pe_ttm = quote.get("pe_ttm", 0)

    forecast = get_consensus_forecast(code)
    eps_fwd = forecast.get("eps_mean", 0) if forecast else 0

    pe_fwd = round(price / eps_fwd, 2) if eps_fwd and eps_fwd > 0 else None
    cagr = forecast.get("cagr", 0) if forecast else 0
    peg = round(pe_fwd / (cagr * 100), 2) if pe_fwd and cagr and cagr > 0 else None

    return {
        "code": code,
        "name": quote.get("name"),
        "price": price,
        "pe_ttm": pe_ttm,
        "pe_fwd": pe_fwd,
        "peg": peg,
        "eps_consensus": eps_fwd,
        "cagr_pct": round(cagr * 100, 2) if cagr else None,
        "mcap_yi": quote.get("mcap_yi"),
        "pb": quote.get("pb"),
    }


def batch_valuation(codes: list[str]) -> list[dict]:
    return [full_valuation(code) for code in codes]


def get_consensus_forecast(code: str) -> dict | None:
    from app.database import get_connection

    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM analyst_forecasts WHERE code=? ORDER BY year LIMIT 1",
        (code,),
    ).fetchone()

    if row:
        return dict(row)

    try:
        from app.datasources.akshare_source import fetch_consensus_forecast
        data = fetch_consensus_forecast(code)
        return data
    except Exception:
        return None
