"""模拟交易API"""
import asyncio
import json
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from datetime import date, datetime

router = APIRouter()

# SSE事件队列
_sse_queues: list[asyncio.Queue] = []


def _broadcast_sse(event: str, data: dict):
    """向所有SSE客户端广播事件"""
    for q in _sse_queues:
        try:
            q.put_nowait({"event": event, "data": data})
        except asyncio.QueueFull:
            pass


def _on_trade_callback(orders: list):
    """自动交易成交回调 → SSE广播"""
    _broadcast_sse("trade", {"orders": orders})
    # 同时更新账户状态
    from app.trading.paper_engine import paper_engine
    _broadcast_sse("status", paper_engine.get_status())


def _on_cycle_callback(status: dict):
    """自动交易周期完成回调"""
    _broadcast_sse("cycle", status)


@router.get("/status")
def get_trade_status():
    """获取模拟交易账户状态(实时行情)"""
    from app.trading.paper_engine import paper_engine
    from app.scanner.full_scanner import batch_tencent_quotes

    codes = list(paper_engine.positions.keys())
    quotes = {}
    if codes:
        quotes = batch_tencent_quotes(codes)

    status = paper_engine.get_status(quotes)
    return {"code": 0, "data": status, "message": "ok"}


@router.get("/stream")
async def trade_stream():
    """SSE实时推送: 交易成交 + 账户状态 + 引擎状态"""
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _sse_queues.append(q)

    async def event_generator():
        try:
            # 初始状态
            from app.trading.paper_engine import paper_engine
            from app.trading.auto_trader import auto_trader
            init_data = {
                "status": paper_engine.get_status(),
                "auto_trader": auto_trader.get_status(),
            }
            yield f"data: {json.dumps({'event': 'init', 'data': init_data}, ensure_ascii=False)}\n\n"

            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=30)
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            _sse_queues.remove(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/auto/start")
def auto_trader_start():
    """启动自动交易引擎"""
    from app.trading.auto_trader import auto_trader
    if auto_trader.is_running:
        return {"code": 0, "data": auto_trader.get_status(), "message": "已在运行中"}
    auto_trader.start()
    return {"code": 0, "data": auto_trader.get_status(), "message": "自动交易已启动"}


@router.post("/auto/stop")
def auto_trader_stop():
    """停止自动交易引擎"""
    from app.trading.auto_trader import auto_trader
    if not auto_trader.is_running:
        return {"code": 0, "data": auto_trader.get_status(), "message": "未在运行"}
    auto_trader.stop()
    return {"code": 0, "data": auto_trader.get_status(), "message": "自动交易已停止"}


@router.get("/auto/status")
def auto_trader_status():
    """获取自动交易引擎状态"""
    from app.trading.auto_trader import auto_trader
    return {"code": 0, "data": auto_trader.get_status(), "message": "ok"}


@router.post("/run")
def run_daily_trading():
    """手动触发每日交易（盘中使用）"""
    from app.trading.paper_engine import paper_engine
    from app.datasources.ths_hot_source import fetch_ths_hot
    from app.strategies.manager import strategy_manager
    from app.api.strategy import _enrich_prices
    from app.scanner.full_scanner import batch_tencent_quotes

    hot_stocks = fetch_ths_hot()
    if not hot_stocks:
        return {"code": 1, "data": None, "message": "无热点数据"}

    hot_stocks = _enrich_prices(hot_stocks)
    signals = strategy_manager.run_all(hot_stocks)

    signal_dicts = []
    codes = set()
    for s in signals:
        signal_dicts.append({
            "code": s.code, "name": s.name, "strategy": s.strategy,
            "signal_type": s.signal_type, "price": s.price,
            "stop_loss": s.stop_loss, "target_price": s.target_price,
            "reason": s.reason, "confidence": s.confidence,
        })
        codes.add(s.code)

    # 获取所有相关股票实时行情
    quotes = batch_tencent_quotes(list(codes))

    # 执行交易
    orders = paper_engine.process_signals(signal_dicts, quotes)
    paper_engine.update_positions(quotes)

    return {
        "code": 0,
        "data": {
            "signals_processed": len(signal_dicts),
            "orders_executed": len(orders),
            "orders": [
                {
                    "code": o.code, "name": o.name,
                    "direction": o.direction, "price": o.price,
                    "volume": o.volume, "strategy": o.strategy,
                }
                for o in orders
            ],
            "status": paper_engine.get_status(),
        },
        "message": "ok",
    }


@router.post("/report")
def generate_report():
    """生成今日交易报告"""
    from app.trading.paper_engine import paper_engine
    from app.scanner.full_scanner import batch_tencent_quotes

    # 更新持仓价格
    codes = list(paper_engine.positions.keys())
    if codes:
        quotes = batch_tencent_quotes(codes)
        paper_engine.update_positions(quotes)

    report = paper_engine.generate_daily_report()
    return {"code": 0, "data": report, "message": "ok"}


@router.get("/report")
def get_report(date_str: str = Query(None, description="日期 YYYY-MM-DD")):
    """获取历史交易报告"""
    from app.database import get_connection
    conn = get_connection()
    if date_str is None:
        date_str = date.today().isoformat()

    row = conn.execute(
        "SELECT report_json FROM trade_reports WHERE date = ?", (date_str,)
    ).fetchone()

    if row:
        import json
        return {"code": 0, "data": json.loads(row["report_json"]), "message": "ok"}
    return {"code": 0, "data": None, "message": "当日无报告"}


@router.get("/reports")
def list_reports(limit: int = Query(10, description="返回条数")):
    """获取交易报告列表"""
    from app.database import get_connection
    conn = get_connection()
    rows = conn.execute(
        """SELECT date, initial_capital, total_value, total_profit,
                  total_profit_pct, today_pnl, position_count, trade_count,
                  buy_count, sell_count, created_at
           FROM trade_reports ORDER BY date DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    return {"code": 0, "data": [dict(r) for r in rows], "message": "ok"}


@router.get("/dashboard")
def trade_dashboard():
    """交易仪表盘(实时)"""
    from app.trading.paper_engine import paper_engine
    from app.scanner.full_scanner import batch_tencent_quotes
    from app.database import get_connection

    codes = list(paper_engine.positions.keys())
    quotes = batch_tencent_quotes(codes) if codes else {}
    status = paper_engine.get_status(quotes)
    conn = get_connection()

    # 近7天报告
    rows = conn.execute(
        """SELECT date, total_value, total_profit, total_profit_pct, today_pnl, trade_count
           FROM trade_reports ORDER BY date DESC LIMIT 7"""
    ).fetchall()

    return {
        "code": 0,
        "data": {
            "current": status,
            "history": [dict(r) for r in rows][::-1],
        },
        "message": "ok",
    }
