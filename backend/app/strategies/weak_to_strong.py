from typing import Optional
from app.strategies.base import BaseStrategy, Signal
from datetime import datetime


class WeakToStrongStrategy(BaseStrategy):
    """弱转强策略 - 识别股票从弱势转为强势的转折信号"""

    # 弱转强关键词（从analyse_text中匹配）
    WEAK_TO_STRONG_KEYWORDS = [
        "拉升", "翻红", "回暖", "反弹", "逆转", "反包",
        "地天板", "翘板", "深水拉起", "尾盘抢筹", "资金回流",
        "涨停板打开后回封", "从跌停拉起", "水下翻红",
    ]

    # 弱势特征关键词
    WEAK_KEYWORDS = [
        "低开", "水下", "跌停", "回调", "杀跌", "炸板",
        "冲高回落", "高开低走", "弱势",
    ]

    def __init__(self):
        super().__init__(
            name="weak_to_strong",
            description="弱转强 - 识别股票从弱势转为强势的信号（量价反转、资金回流、翘板等）"
        )

    def _check_keyword_match(self, text: str, keywords: list) -> int:
        """返回匹配到的关键词数量"""
        if not text:
            return 0
        return sum(1 for kw in keywords if kw in text)

    def _is_weak_background(self, stock_data: dict) -> bool:
        """判断是否有弱势背景（先弱才能转强）"""
        analyse = stock_data.get("analyse", "")
        reason = stock_data.get("reason", "")
        text = f"{analyse} {reason}"
        return self._check_keyword_match(text, self.WEAK_KEYWORDS) > 0

    def _has_reversal_signal(self, stock_data: dict) -> int:
        """检测反转信号强度，返回匹配数"""
        analyse = stock_data.get("analyse", "")
        reason = stock_data.get("reason", "")
        text = f"{analyse} {reason}"
        return self._check_keyword_match(text, self.WEAK_TO_STRONG_KEYWORDS)

    def check_conditions(self, stock_data: dict) -> Optional[Signal]:
        code = stock_data.get("code", "")
        name = stock_data.get("name", "")
        price = stock_data.get("close_price", 0) or stock_data.get("price", 0)
        change_pct = stock_data.get("change_pct", 0)
        hot_score = stock_data.get("hot_score", 0)
        concept_tags = stock_data.get("concept_tags", [])
        popularity_tag = stock_data.get("popularity_tag", "")
        reason = stock_data.get("reason", "")
        analyse = stock_data.get("analyse", "")

        if not code:
            return None

        score = 0
        reasons = []

        # 1. 反转信号检测（核心条件）
        reversal_count = self._has_reversal_signal(stock_data)
        if reversal_count >= 2:
            score += 30
            reasons.append(f"强反转信号({reversal_count}个关键特征)")
        elif reversal_count == 1:
            score += 20
            reasons.append("反转信号")

        # 2. 弱势背景确认（有弱势才有弱转强）
        if self._is_weak_background(stock_data):
            score += 15
            reasons.append("弱势背景确认")

        # 3. 涨幅适中（0-5%是弱转强的典型区间）
        if change_pct and 0 < change_pct <= 5:
            score += 15
            reasons.append(f"涨幅{change_pct:.1f}%（弱转强区间）")
        elif change_pct and 5 < change_pct <= 9.5:
            score += 10
            reasons.append(f"涨幅{change_pct:.1f}%（转强加速）")

        # 4. 热度验证（热度适中说明有资金关注）
        if hot_score and hot_score > 100000:
            score += 10
            reasons.append(f"热度{(hot_score/10000):.0f}万")
        elif hot_score and hot_score > 50000:
            score += 5
            reasons.append(f"热度适中")

        # 5. 题材支撑
        if concept_tags and len(concept_tags) >= 2:
            score += 10
            reasons.append(f"题材: {', '.join(concept_tags[:3])}")
        elif concept_tags:
            score += 5
            reasons.append(f"题材: {concept_tags[0]}")

        # 6. 连板状态（非高位板更可能是弱转强起点）
        if not popularity_tag or "板" not in popularity_tag:
            score += 10
            reasons.append("低位启动")
        elif "首板" in popularity_tag or "2天" in popularity_tag:
            score += 8
            reasons.append(f"低位板({popularity_tag})")
        elif "3天" in popularity_tag:
            score += 3
            reasons.append(f"三板确认({popularity_tag})")

        # 7. 驱动事件
        if reason:
            score += 5
            reasons.append(f"驱动: {reason[:30]}")

        # 弱转强需要至少弱势背景或反转信号
        has_weak_bg = self._is_weak_background(stock_data)
        has_reversal = reversal_count > 0
        if not has_weak_bg and not has_reversal:
            return None

        # 最低得分要求
        if score < 30:
            return None

        if not price:
            price = 10.0

        # 风险收益比：弱转强止损空间小，目标空间大
        stop_loss_pct = 0.04
        target_pct = 0.12

        stop_loss = self.calculate_stop_loss(price, stop_loss_pct)
        target = self.calculate_target(price, target_pct)

        # 信心度基于得分
        confidence = min(95, max(45, score))

        holding_days = 3 if reversal_count >= 2 else 2

        return Signal(
            code=code,
            name=name,
            strategy=self.name,
            signal_type="buy",
            price=price,
            stop_loss=stop_loss,
            target_price=target,
            reason=" | ".join(reasons),
            risk="弱转强失败风险：可能再次走弱，需严格止损，警惕假突破",
            confidence=confidence,
            holding_days=holding_days,
            created_at=datetime.now().isoformat()
        )

    def get_buy_reason(self, stock_data: dict) -> str:
        return "弱转强信号确认，资金介入明显，有望从弱势转为强势，风险收益比佳"

    def get_risk(self, stock_data: dict) -> str:
        return "弱转强失败风险：可能再次走弱回到弱势区间，严格执行止损纪律，警惕无量假突破"
