from datetime import datetime
from typing import Dict, List
from app.strategies.manager import strategy_manager
from app.strategies.sentiment import sentiment_model
from app.factors.manager import factor_manager
from app.risk.manager import risk_manager
from app.recommendation.daily import daily_recommender
from app.datasources.ths_hot_source import fetch_ths_hot
from app.datasources.tencent_source import fetch_tencent_quote


class MarketMonitor:
    """市场监控器"""

    def __init__(self):
        self.monitoring = False
        self.last_report = None
        self.alerts: List[Dict] = []

    def start_monitoring(self):
        """开始监控"""
        self.monitoring = True
        self._run_monitoring_cycle()

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False

    def _run_monitoring_cycle(self):
        """运行监控周期"""
        if not self.monitoring:
            return

        # 获取市场数据
        hot_stocks = fetch_ths_hot()

        # 分析市场情绪
        sentiment = sentiment_model.analyze(hot_stocks)

        # 检查风险
        risk_level = "LOW"
        if sentiment["stage"] in ["高潮期", "退潮期"]:
            risk_level = "HIGH"

        # 生成警报
        if risk_level == "HIGH":
            self.alerts.append({
                "time": datetime.now().isoformat(),
                "type": "risk",
                "level": risk_level,
                "message": f"市场情绪{sentiment['stage']}，建议注意风险"
            })

        # 检查涨停异动
        limit_up_count = sentiment.get("limit_up_count", 0)
        if limit_up_count > 50:
            self.alerts.append({
                "time": datetime.now().isoformat(),
                "type": "anomaly",
                "level": "HIGH",
                "message": f"涨停数量异常: {limit_up_count}只"
            })

    def generate_report(self) -> Dict:
        """生成监控报告"""
        hot_stocks = fetch_ths_hot()

        # 市场情绪
        sentiment = sentiment_model.analyze(hot_stocks)

        # 策略信号
        signals = strategy_manager.run_all(hot_stocks)

        # 因子排名
        factor_ranking = factor_manager.get_top_stocks(hot_stocks, 10)

        # 每日推荐
        recommendations = daily_recommender.generate()

        # 风险评估
        risk_assessment = risk_manager.check_recommendations(
            recommendations.get("recommendations", [])
        )

        report = {
            "timestamp": datetime.now().isoformat(),
            "market_overview": {
                "sentiment": sentiment,
                "hot_stocks_count": len(hot_stocks),
                "signals_count": len(signals)
            },
            "top_signals": [
                {
                    "code": s.code,
                    "name": s.name,
                    "strategy": s.strategy,
                    "confidence": s.confidence,
                    "reason": s.reason[:50]
                }
                for s in signals[:10]
            ],
            "factor_ranking": factor_ranking[:5],
            "recommendations": recommendations.get("recommendations", [])[:5],
            "risk_alerts": self.alerts[-10:],
            "risk_assessment": {
                "blocked": sum(1 for r in risk_assessment if r.get("risk_level") == "BLOCK"),
                "high_risk": sum(1 for r in risk_assessment if r.get("risk_level") == "HIGH"),
                "medium_risk": sum(1 for r in risk_assessment if r.get("risk_level") == "MEDIUM"),
                "low_risk": sum(1 for r in risk_assessment if r.get("risk_level") == "LOW")
            }
        }

        self.last_report = report
        return report

    def get_alerts(self, limit: int = 20) -> List[Dict]:
        """获取警报"""
        return self.alerts[-limit:]


market_monitor = MarketMonitor()
