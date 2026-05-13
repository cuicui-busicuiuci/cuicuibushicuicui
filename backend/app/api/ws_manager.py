import asyncio
import json
from datetime import datetime
from typing import Set
from fastapi import WebSocket


class WSManager:
    """WebSocket连接管理器，负责客户端连接和实时数据广播"""

    def __init__(self):
        self.connections: Set[WebSocket] = set()
        self._broadcast_task = None

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.add(ws)
        print(f"[WS] 客户端连接, 当前连接数: {len(self.connections)}")

    async def disconnect(self, ws: WebSocket):
        self.connections.discard(ws)
        print(f"[WS] 客户端断开, 当前连接数: {len(self.connections)}")

    async def broadcast(self, data: dict):
        """向所有连接的客户端广播数据"""
        if not self.connections:
            return
        message = json.dumps(data, ensure_ascii=False)
        dead: Set[WebSocket] = set()
        for ws in self.connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self.connections -= dead

    async def send_to(self, ws: WebSocket, data: dict):
        """向单个客户端发送数据"""
        try:
            await ws.send_text(json.dumps(data, ensure_ascii=False))
        except Exception:
            self.connections.discard(ws)

    @property
    def active_count(self) -> int:
        return len(self.connections)


ws_manager = WSManager()


def gather_market_data() -> dict:
    """收集全量市场数据"""
    from app.datasources.ths_hot_source import fetch_ths_hot
    from app.strategies.manager import strategy_manager
    from app.strategies.sentiment import sentiment_model
    from app.recommendation.daily import daily_recommender

    hot_stocks = fetch_ths_hot()
    if not hot_stocks:
        return {"type": "market_snapshot", "timestamp": datetime.now().isoformat(), "error": "无数据"}

    # 补充腾讯实时价格
    from app.api.strategy import _enrich_prices
    hot_stocks = _enrich_prices(hot_stocks)

    sentiment = sentiment_model.analyze(hot_stocks)

    strategies = {}
    for s in strategy_manager.strategies:
        signals = strategy_manager.run_strategy(s.name, hot_stocks)
        strategies[s.name] = [
            {
                "code": sig.code, "name": sig.name, "price": sig.price,
                "stop_loss": sig.stop_loss, "target_price": sig.target_price,
                "reason": sig.reason, "risk": sig.risk, "confidence": sig.confidence,
            }
            for sig in signals
        ]

    try:
        rec = daily_recommender.generate()
        recommendations = rec.get("recommendations", [])[:10]
        # 持久化推荐和信号
        try:
            from app.db.persistence import save_daily_recommendations, save_strategy_signals
            save_daily_recommendations(rec)
            save_strategy_signals(strategies)
        except Exception:
            pass
    except Exception:
        recommendations = []

    top_hot = [
        {
            "code": h["code"], "name": h["name"], "change_pct": h.get("change_pct", 0),
            "hot_score": h.get("hot_score", 0), "concept_tags": h.get("concept_tags", [])[:3],
            "popularity_tag": h.get("popularity_tag", ""), "reason": h.get("reason", "")[:40],
        }
        for h in hot_stocks[:15]
    ]

    return {
        "type": "market_snapshot",
        "timestamp": datetime.now().isoformat(),
        "sentiment": sentiment,
        "strategies": strategies,
        "recommendations": recommendations,
        "hot_stocks": top_hot,
        "total_signals": sum(len(v) for v in strategies.values()),
    }
