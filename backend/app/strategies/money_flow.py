from typing import Optional
from app.strategies.base import BaseStrategy, Signal
from datetime import datetime


class MoneyFlowStrategy(BaseStrategy):
    """资金流策略 - 跟踪主力资金流入流出，捕捉资金合力"""

    # 资金流入关键词
    INFLOW_KEYWORDS = [
        "主力流入", "大单买入", "机构买入", "游资买入", "资金抢筹",
        "大单净流入", "主力加仓", "资金建仓", "底部吸筹", "资金介入",
        "放量拉升", "资金回流", "大资金", "主力资金", "资金追捧",
        "净买入", "加仓", "增持", "机构加仓",
    ]

    # 资金合力关键词（多路资金同时进场）
    SYNERGY_KEYWORDS = [
        "游资", "机构", "北向", "主力", "敢死队", "杭州帮",
        "上海帮", "宁波帮", "深圳帮", "佛山帮", "成都帮",
    ]

    # 出货/流出关键词（排除项）
    OUTFLOW_KEYWORDS = [
        "主力出货", "资金出逃", "大单卖出", "减持", "套现",
        "砸盘", "出货", "获利了结", "资金撤离",
    ]

    def __init__(self):
        super().__init__(
            name="money_flow",
            description="资金流 - 跟踪主力资金流向，捕捉多路资金合力共振的信号"
        )

    def _count_keywords(self, text: str, keywords: list) -> int:
        if not text:
            return 0
        return sum(1 for kw in keywords if kw in text)

    def _has_outflow_signal(self, stock_data: dict) -> bool:
        """检测是否有出货信号（如果有则不适合买入）"""
        analyse = stock_data.get("analyse", "")
        reason = stock_data.get("reason", "")
        return self._count_keywords(f"{analyse} {reason}", self.OUTFLOW_KEYWORDS) > 0

    def _count_inflow_signals(self, stock_data: dict) -> int:
        """统计资金流入信号强度"""
        analyse = stock_data.get("analyse", "")
        reason = stock_data.get("reason", "")
        return self._count_keywords(f"{analyse} {reason}", self.INFLOW_KEYWORDS)

    def _count_synergy(self, stock_data: dict) -> int:
        """统计资金合力信号（多路资金共振）"""
        analyse = stock_data.get("analyse", "")
        reason = stock_data.get("reason", "")
        return self._count_keywords(f"{analyse} {reason}", self.SYNERGY_KEYWORDS)

    def check_conditions(self, stock_data: dict) -> Optional[Signal]:
        code = stock_data.get("code", "")
        name = stock_data.get("name", "")
        price = stock_data.get("close_price", 0) or stock_data.get("price", 0)
        change_pct = stock_data.get("change_pct", 0)
        hot_score = stock_data.get("hot_score", 0)
        concept_tags = stock_data.get("concept_tags", [])
        popularity_tag = stock_data.get("popularity_tag", "")
        reason = stock_data.get("reason", "")

        if not code:
            return None

        # 排除出货信号
        if self._has_outflow_signal(stock_data):
            return None

        score = 0
        reasons = []

        # 1. 资金流入信号（核心）
        inflow_count = self._count_inflow_signals(stock_data)
        if inflow_count >= 3:
            score += 35
            reasons.append(f"强资金流入({inflow_count}个信号)")
        elif inflow_count >= 2:
            score += 25
            reasons.append("资金流入明显")
        elif inflow_count == 1:
            score += 15
            reasons.append("资金流入")

        # 2. 资金合力检测（多路资金共振是最强信号）
        synergy_count = self._count_synergy(stock_data)
        if synergy_count >= 3:
            score += 25
            reasons.append(f"多路资金共振({synergy_count}路)")
        elif synergy_count >= 2:
            score += 18
            reasons.append("资金合力")
        elif synergy_count == 1:
            score += 8
            reasons.append("有资金关注")

        # 3. 涨幅验证（资金推动的涨幅）
        if change_pct and 0 < change_pct <= 3:
            score += 8
            reasons.append(f"涨幅{change_pct:.1f}%（建仓阶段）")
        elif change_pct and 3 < change_pct <= 7:
            score += 15
            reasons.append(f"涨幅{change_pct:.1f}%（拉升阶段）")
        elif change_pct and 7 < change_pct <= 9.5:
            score += 10
            reasons.append(f"涨幅{change_pct:.1f}%（加速阶段）")
        elif change_pct and change_pct > 9.5:
            score += 5
            reasons.append(f"涨停（关注开板风险）")

        # 4. 热度验证（热度=资金关注度的代理指标）
        if hot_score and hot_score > 300000:
            score += 12
            reasons.append(f"高热度{(hot_score/10000):.0f}万")
        elif hot_score and hot_score > 100000:
            score += 8
            reasons.append(f"热度{(hot_score/10000):.0f}万")
        elif hot_score and hot_score > 30000:
            score += 5
            reasons.append("热度适中")

        # 5. 题材验证（热门题材吸引资金）
        if concept_tags and len(concept_tags) >= 3:
            score += 8
            reasons.append(f"多题材: {', '.join(concept_tags[:3])}")
        elif concept_tags:
            score += 4
            reasons.append(f"题材: {concept_tags[0]}")

        # 6. 连板状态（低位板更安全，资金刚介入）
        if not popularity_tag:
            score += 5
            reasons.append("首板潜力")
        elif "首板" in popularity_tag or "2天" in popularity_tag:
            score += 8
            reasons.append(f"连板早期({popularity_tag})")
        elif "3天" in popularity_tag:
            score += 3
            reasons.append("三板")
        elif "4天" in popularity_tag or "5天" in popularity_tag:
            score += 0
            reasons.append(f"高标({popularity_tag})，注意风险")

        # 7. 事件驱动
        if reason:
            score += 5
            reasons.append(f"事件: {reason[:25]}")

        # 必须有资金流入信号
        if inflow_count == 0:
            return None

        if score < 25:
            return None

        if not price:
            price = 10.0

        stop_loss = self.calculate_stop_loss(price, 0.05)
        target = self.calculate_target(price, 0.15)

        confidence = min(92, max(40, score))

        holding_days = 5 if synergy_count >= 3 else 3

        return Signal(
            code=code,
            name=name,
            strategy=self.name,
            signal_type="buy",
            price=price,
            stop_loss=stop_loss,
            target_price=target,
            reason=" | ".join(reasons),
            risk="资金流出风险：主力可能随时撤离，关注资金流向变化，避免追高",
            confidence=confidence,
            holding_days=holding_days,
            created_at=datetime.now().isoformat()
        )

    def get_buy_reason(self, stock_data: dict) -> str:
        return "主力资金持续流入，多路资金合力，量价配合良好，有望继续走强"

    def get_risk(self, stock_data: dict) -> str:
        return "资金流出风险：主力资金可能随时撤离，需密切关注资金流向变化，避免高位接盘"
