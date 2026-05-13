from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime
from app.strategies.manager import strategy_manager
from app.strategies.sentiment import sentiment_model
from app.datasources.ths_hot_source import fetch_ths_hot


@dataclass
class Recommendation:
    code: str
    name: str
    strategy: str
    signal_type: str
    price: float
    stop_loss: float
    target_price: float
    reason: str
    risk: str
    confidence: float
    holding_days: int
    level: str  # 强推荐/普通推荐/观察


class DailyRecommender:
    """每日推荐系统"""

    def __init__(self):
        self.max_recommendations = 10
        self.max_strong推荐 = 3

    def generate(self) -> Dict:
        """生成每日推荐"""
        hot_stocks = fetch_ths_hot()
        if not hot_stocks:
            return {"error": "无热点数据"}

        # 补充腾讯实时价格
        try:
            from app.api.strategy import _enrich_prices
            hot_stocks = _enrich_prices(hot_stocks)
        except Exception:
            pass

        # 获取市场情绪
        sentiment = sentiment_model.analyze(hot_stocks)

        # 运行所有策略
        signals = strategy_manager.run_all(hot_stocks)

        # 按置信度排序
        signals.sort(key=lambda s: s.confidence, reverse=True)

        # 去重（同一股票只保留最高置信度信号）
        seen_codes = set()
        unique_signals = []
        for signal in signals:
            if signal.code not in seen_codes:
                seen_codes.add(signal.code)
                unique_signals.append(signal)

        # 生成推荐
        recommendations = []
        for signal in unique_signals[:self.max_recommendations]:
            level = self._determine_level(signal.confidence)
            recommendations.append(Recommendation(
                code=signal.code,
                name=signal.name,
                strategy=signal.strategy,
                signal_type=signal.signal_type,
                price=signal.price,
                stop_loss=signal.stop_loss,
                target_price=signal.target_price,
                reason=signal.reason,
                risk=signal.risk,
                confidence=signal.confidence,
                holding_days=signal.holding_days,
                level=level
            ))

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "market_sentiment": sentiment,
            "recommendations": [
                {
                    "code": r.code,
                    "name": r.name,
                    "strategy": r.strategy,
                    "price": r.price,
                    "stop_loss": r.stop_loss,
                    "target_price": r.target_price,
                    "reason": r.reason,
                    "risk": r.risk,
                    "confidence": r.confidence,
                    "holding_days": r.holding_days,
                    "level": r.level
                }
                for r in recommendations
            ],
            "total_signals": len(signals),
            "recommended_count": len(recommendations)
        }

    def _determine_level(self, confidence: float) -> str:
        """确定推荐等级"""
        if confidence >= 80:
            return "强推荐"
        elif confidence >= 70:
            return "普通推荐"
        else:
            return "观察"


daily_recommender = DailyRecommender()
