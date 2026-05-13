from typing import Optional
from app.strategies.base import BaseStrategy, Signal
from datetime import datetime


class MainWaveStrategy(BaseStrategy):
    """主升浪策略"""

    def __init__(self):
        super().__init__(
            name="main_wave",
            description="主升浪 - 捕捉股票主升浪行情，持股待涨"
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

        # 主升浪条件
        is_main_wave = False
        reasons = []

        # 1. 涨幅适中（3%-7%）
        if change_pct and 3 < change_pct < 7:
            is_main_wave = True
            reasons.append(f"涨幅: {change_pct:.2f}%")

        # 2. 热度高
        if hot_score and hot_score > 500000:
            reasons.append(f"热度: {hot_score:.0f}")

        # 3. 有题材驱动
        if concept_tags:
            reasons.append(f"题材: {', '.join(concept_tags[:3])}")

        # 4. 有明确原因
        if reason:
            reasons.append(f"驱动: {reason}")

        if not is_main_wave or len(reasons) < 2:
            return None

        if not price:
            price = 10.0

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
            risk="主升浪结束风险，注意止盈",
            confidence=70,
            holding_days=5,
            created_at=datetime.now().isoformat()
        )

    def get_buy_reason(self, stock_data: dict) -> str:
        return "主升浪启动，资金合力，持股待涨"

    def get_risk(self, stock_data: dict) -> str:
        return "主升浪结束风险，注意止盈，避免追高被套"
