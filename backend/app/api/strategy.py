from fastapi import APIRouter, Query

router = APIRouter()


def _enrich_prices(stocks: list) -> list:
    """用腾讯API补充实时价格到股票数据"""
    if not stocks:
        return stocks
    try:
        from app.scanner.full_scanner import batch_tencent_quotes
        codes = [s.get("code", "") for s in stocks if s.get("code")]
        quotes = batch_tencent_quotes(codes)
        for s in stocks:
            code = s.get("code", "")
            q = quotes.get(code, {})
            if q and q.get("price", 0) > 0:
                s["price"] = q["price"]
                s["close_price"] = q["price"]
                s["change_pct"] = q.get("change_pct", s.get("change_pct", 0))
                s["turnover_pct"] = q.get("turnover_pct", 0)
                s["pe_ttm"] = q.get("pe_ttm", 0)
                s["pb"] = q.get("pb", 0)
                s["mcap"] = q.get("mcap_yi", 0)
                s["volume"] = q.get("amount_wan", 0)
            elif not s.get("price") or s.get("price") == 0:
                s["price"] = round(float(s.get("close_price", 0) or 0), 2)
    except Exception as e:
        print(f"价格补充失败: {e}")
    return stocks


@router.get("/")
def list_strategies():
    from app.strategies.manager import strategy_manager
    data = strategy_manager.list_strategies()
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/signals")
def get_signals(strategy: str = Query(None, description="策略名称")):
    from app.strategies.manager import strategy_manager
    from app.datasources.ths_hot_source import fetch_ths_hot

    hot_stocks = fetch_ths_hot()
    if not hot_stocks:
        return {"code": 0, "data": [], "message": "无热点数据"}

    hot_stocks = _enrich_prices(hot_stocks)

    # 构建代码→数据映射用于补充字段
    stock_map = {s.get("code", ""): s for s in hot_stocks}

    if strategy:
        signals = strategy_manager.run_strategy(strategy, hot_stocks)
    else:
        signals = strategy_manager.run_all(hot_stocks)

    result = []
    for s in signals:
        extra = stock_map.get(s.code, {})
        result.append({
            "code": s.code, "name": s.name, "strategy": s.strategy,
            "signal_type": s.signal_type, "price": s.price,
            "stop_loss": s.stop_loss, "target_price": s.target_price,
            "reason": s.reason, "risk": s.risk,
            "confidence": s.confidence, "holding_days": s.holding_days,
            "mcap": extra.get("mcap", 0),
            "turnover_pct": extra.get("turnover_pct", 0),
            "pe_ttm": extra.get("pe_ttm", 0),
            "pb": extra.get("pb", 0),
        })

    return {"code": 0, "data": result, "message": "ok"}


@router.get("/leader")
def get_leader_signals():
    from app.strategies.manager import strategy_manager
    from app.datasources.ths_hot_source import fetch_ths_hot

    hot_stocks = fetch_ths_hot()
    hot_stocks = _enrich_prices(hot_stocks)
    stock_map = {s.get("code", ""): s for s in hot_stocks}
    signals = strategy_manager.run_strategy("leader", hot_stocks)

    result = [
        {
            "code": s.code, "name": s.name, "price": s.price,
            "stop_loss": s.stop_loss, "target_price": s.target_price,
            "reason": s.reason, "risk": s.risk, "confidence": s.confidence,
            "mcap": stock_map.get(s.code, {}).get("mcap", 0),
            "turnover_pct": stock_map.get(s.code, {}).get("turnover_pct", 0),
            "pe_ttm": stock_map.get(s.code, {}).get("pe_ttm", 0),
        }
        for s in signals
    ]

    return {"code": 0, "data": result, "message": "ok"}


@router.get("/first-board")
def get_first_board_signals():
    from app.strategies.manager import strategy_manager
    from app.datasources.ths_hot_source import fetch_ths_hot

    hot_stocks = fetch_ths_hot()
    hot_stocks = _enrich_prices(hot_stocks)
    stock_map = {s.get("code", ""): s for s in hot_stocks}
    signals = strategy_manager.run_strategy("first_board", hot_stocks)

    result = [
        {
            "code": s.code, "name": s.name, "price": s.price,
            "stop_loss": s.stop_loss, "target_price": s.target_price,
            "reason": s.reason, "risk": s.risk, "confidence": s.confidence,
            "mcap": stock_map.get(s.code, {}).get("mcap", 0),
            "turnover_pct": stock_map.get(s.code, {}).get("turnover_pct", 0),
            "pe_ttm": stock_map.get(s.code, {}).get("pe_ttm", 0),
        }
        for s in signals
    ]

    return {"code": 0, "data": result, "message": "ok"}


@router.get("/sentiment")
def get_market_sentiment():
    from app.strategies.sentiment import sentiment_model
    from app.datasources.ths_hot_source import fetch_ths_hot

    hot_stocks = fetch_ths_hot()
    data = sentiment_model.analyze(hot_stocks)
    return {"code": 0, "data": data, "message": "ok"}
