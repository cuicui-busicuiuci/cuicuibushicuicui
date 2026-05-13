from typing import Optional
from app.strategies.base import BaseStrategy, Signal
from datetime import datetime


class LeaderStrategy(BaseStrategy):
    """龙头战法策略"""

    def __init__(self):
        super().__init__(
            name="leader",
            description="龙头战法 - 识别板块龙头股，捕捉主升浪行情"
        )

    def check_conditions(self, stock_data: dict) -> Optional[Signal]:
        code = stock_data.get("code", "")
        name = stock_data.get("name", "")
        price = stock_data.get("price", 0)
        change_pct = stock_data.get("change_pct", 0)
        hot_score = stock_data.get("hot_score", 0)
        concept_tags = stock_data.get("concept_tags", [])
        popularity_tag = stock_data.get("popularity_tag", "")
        reason = stock_data.get("reason", "")

        if not code:
            return None

        # 龙头股条件
        is_leader = False
        reasons = []

        # 1. 连续涨停（4天4板以上）
        if popularity_tag and "板" in popularity_tag:
            is_leader = True
            reasons.append(f"连板高度: {popularity_tag}")

        # 2. 热度分数高
        if hot_score and hot_score > 500000:
            is_leader = True
            reasons.append(f"热度分数: {hot_score:.0f}")

        # 3. 涨幅大于5%
        if change_pct and change_pct > 5:
            reasons.append(f"涨幅: {change_pct:.2f}%")

        # 4. 有题材驱动
        if concept_tags:
            reasons.append(f"题材: {', '.join(concept_tags[:3])}")

        # 5. 有明确原因
        if reason:
            reasons.append(f"驱动: {reason}")

        if not is_leader or len(reasons) < 2:
            return None

        # 使用当前价格（如果没有价格，使用涨幅推算）
        if not price:
            price = 10.0  # 默认价格

        stop_loss = self.calculate_stop_loss(price, 0.05)
        target = self.calculate_target(price, 0.20)

        return Signal(
            code=code,
            name=name,
            strategy=self.name,
            signal_type="buy",
            price=price,
            stop_loss=stop_loss,
            target_price=target,
            reason=" + ".join(reasons),
            risk="高位接力风险，注意止损",
            confidence=75,
            holding_days=3,
            created_at=datetime.now().isoformat()
        )

    def get_buy_reason(self, stock_data: dict) -> str:
        return "板块龙头，资金合力，有望继续走强"

    def get_risk(self, stock_data: dict) -> str:
        return "高位接力风险，注意止损，避免追高被套"
