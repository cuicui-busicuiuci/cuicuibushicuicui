from typing import Optional
from app.strategies.base import BaseStrategy, Signal
from datetime import datetime


class LeaderDipStrategy(BaseStrategy):
    """龙头低吸策略"""

    def __init__(self):
        super().__init__(
            name="leader_dip",
            description="龙头低吸 - 在龙头股回调时低吸，博取二波行情"
        )

    def check_conditions(self, stock_data: dict) -> Optional[Signal]:
        code = stock_data.get("code", "")
        name = stock_data.get("name", "")
        price = stock_data.get("price", 0)
        change_pct = stock_data.get("change_pct", 0)
        concept_tags = stock_data.get("concept_tags", [])
        popularity_tag = stock_data.get("popularity_tag", "")
        reason = stock_data.get("reason", "")
        hot_score = stock_data.get("hot_score", 0)

        if not code:
            return None

        # 龙头低吸条件
        is_leader_dip = False
        reasons = []

        # 1. 曾经是龙头（有连板历史）
        if popularity_tag and "板" in popularity_tag:
            is_leader_dip = True
            reasons.append(f"龙头历史: {popularity_tag}")

        # 2. 当前回调（涨幅在-3%到3%之间）
        if change_pct and -3 < change_pct < 3:
            reasons.append(f"回调中: {change_pct:.2f}%")

        # 3. 热度仍在
        if hot_score and hot_score > 300000:
            reasons.append(f"热度: {hot_score:.0f}")

        # 4. 有题材驱动
        if concept_tags:
            reasons.append(f"题材: {', '.join(concept_tags[:3])}")

        if not is_leader_dip or len(reasons) < 2:
            return None

        if not price:
            price = 10.0

        stop_loss = self.calculate_stop_loss(price, 0.05)
        target = self.calculate_target(price, 0.15)

        return Signal(
            code=code,
            name=name,
            strategy=self.name,
            signal_type="buy",
            price=price,
            stop_loss=stop_loss,
            target_price=target,
            reason=" + ".join(reasons),
            risk="二波失败风险，注意止损",
            confidence=65,
            holding_days=3,
            created_at=datetime.now().isoformat()
        )

    def get_buy_reason(self, stock_data: dict) -> str:
        return "龙头回调到位，资金回流，有望开启二波"

    def get_risk(self, stock_data: dict) -> str:
        return "二波失败风险，注意止损，避免抄底被套"
