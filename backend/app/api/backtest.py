from fastapi import APIRouter, Query

router = APIRouter()


@router.post("/run")
def run_backtest(strategy: str = Query(None, description="策略名称"), days: int = Query(60, description="回测天数")):
    from app.backtest.engine import backtest_engine
    from app.strategies.manager import strategy_manager
    from app.datasources.ths_hot_source import fetch_ths_hot
    from app.datasources.mootdx_source import fetch_kline

    hot_stocks = fetch_ths_hot()
    if not hot_stocks:
        return {"code": 0, "data": None, "message": "无热点数据"}

    if strategy:
        signals = strategy_manager.run_strategy(strategy, hot_stocks)
    else:
        signals = strategy_manager.run_all(hot_stocks)

    signal_dicts = [
        {
            "code": s.code,
            "name": s.name,
            "price": s.price,
            "stop_loss": s.stop_loss,
            "target_price": s.target_price,
            "strategy": s.strategy,
            "reason": s.reason,
        }
        for s in signals
    ]

    # 获取K线数据用于真实回测
    kline_data = {}
    codes = list(set(s["code"] for s in signal_dicts))
    for code in codes[:20]:  # 限制获取20只，避免太慢
        try:
            klines = fetch_kline(code, category=4, limit=days)
            if klines:
                kline_data[code] = klines
        except Exception:
            pass

    result = backtest_engine.run(signal_dicts, kline_data)

    # Top trades
    top_trades = sorted(result.trades, key=lambda t: t.profit_pct, reverse=True)
    trade_list = [
        {
            "code": t.code, "name": t.name, "strategy": t.strategy,
            "buy_date": t.buy_date, "buy_price": t.buy_price,
            "sell_date": t.sell_date, "sell_price": t.sell_price,
            "profit_pct": t.profit_pct, "holding_days": t.holding_days,
            "reason": t.reason,
        }
        for t in top_trades[:20]
    ]

    return {
        "code": 0,
        "data": {
            "total_return": result.total_return,
            "annual_return": result.annual_return,
            "max_drawdown": result.max_drawdown,
            "sharpe_ratio": result.sharpe_ratio,
            "win_rate": result.win_rate,
            "profit_loss_ratio": result.profit_loss_ratio,
            "avg_holding_days": result.avg_holding_days,
            "max_consecutive_loss": result.max_consecutive_loss,
            "total_trades": result.total_trades,
            "winning_trades": result.winning_trades,
            "losing_trades": result.losing_trades,
            "trades": trade_list,
            "kline_count": len(kline_data),
        },
        "message": "ok"
    }


@router.post("/strategy/{strategy_name}")
def run_strategy_backtest(
    strategy_name: str,
    days: int = Query(60, description="回测天数"),
):
    """单独回测某个策略"""
    return run_backtest(strategy=strategy_name, days=days)
