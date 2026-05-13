from typing import Optional
from app.strategies.base import BaseStrategy, Signal
from datetime import datetime


class FirstBoardStrategy(BaseStrategy):
    """首板战法策略"""

    def __init__(self):
        super().__init__(
            name="first_board",
            description="首板战法 - 捕捉首次涨停股票，博取次日溢价"
        )

    def check_conditions(self, stock_data: dict) -> Optional[Signal]:
        code = stock_data.get("code", "")
        name = stock_data.get("name", "")
        price = stock_data.get("price", 0)
        change_pct = stock_data.get("change_pct", 0)
        concept_tags = stock_data.get("concept_tags", [])
        popularity_tag = stock_data.get("popularity_tag", "")
        reason = stock_data.get("reason", "")

        if not code:
            return None

        # 首板条件
        is_first_board = False
        reasons = []

        # 1. 涨停（涨幅>=9.9%）
        if change_pct and change_pct >= 9.9:
            is_first_board = True
            reasons.append(f"涨停: {change_pct:.2f}%")

        # 2. 首板（非连板）
        if popularity_tag and "首板" in popularity_tag:
            reasons.append("首板涨停")

        # 3. 有题材驱动
        if concept_tags:
            reasons.append(f"题材: {', '.join(concept_tags[:3])}")

        # 4. 有明确原因
        if reason:
            reasons.append(f"驱动: {reason}")

        if not is_first_board or len(reasons) < 2:
            return None

        if not price:
            price = 10.0

        stop_loss = self.calculate_stop_loss(price, 0.05)
        target = self.calculate_target(price, 0.10)

        return Signal(
            code=code,
            name=name,
            strategy=self.name,
            signal_type="buy",
            price=price,
            stop_loss=stop_loss,
            target_price=target,
            reason=" + ".join(reasons),
            risk="次日低开风险，注意竞价表现",
            confidence=70,
            holding_days=1,
            created_at=datetime.now().isoformat()
        )

    def get_buy_reason(self, stock_data: dict) -> str:
        return "首板涨停，题材驱动，博取次日溢价"

    def get_risk(self, stock_data: dict) -> str:
        return "次日低开风险，注意竞价表现，及时止盈止损"
