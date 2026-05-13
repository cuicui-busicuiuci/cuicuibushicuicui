from typing import Optional
from app.factors.base import BaseFactor, FactorResult


class ChangePctFactor(BaseFactor):
    """涨跌幅因子"""

    def __init__(self):
        super().__init__(
            name="change_pct",
            description="涨跌幅因子 - 评估股票涨跌幅的合理性",
            weight=0.15
        )

    def calculate(self, stock_data: dict) -> Optional[FactorResult]:
        code = stock_data.get("code", "")
        name = stock_data.get("name", "")
        change_pct = stock_data.get("change_pct", 0)

        if not code:
            return None

        # 涨幅适中（3%-7%）得分最高
        if 3 <= change_pct <= 7:
            score = 90
        elif 0 < change_pct < 3:
            score = 70
        elif 7 < change_pct < 10:
            score = 60
        elif change_pct >= 10:
            score = 50
        else:
            score = 30

        return FactorResult(
            code=code,
            name=name,
            factor_name=self.name,
            score=score,
            detail=f"涨幅: {change_pct:.2f}%"
        )


class HotScoreFactor(BaseFactor):
    """热度因子"""

    def __init__(self):
        super().__init__(
            name="hot_score",
            description="热度因子 - 评估股票的市场关注度",
            weight=0.20
        )

    def calculate(self, stock_data: dict) -> Optional[FactorResult]:
        code = stock_data.get("code", "")
        name = stock_data.get("name", "")
        hot_score = stock_data.get("hot_score", 0)

        if not code:
            return None

        # 热度分数归一化
        score = self.normalize(hot_score, 0, 1000000)

        return FactorResult(
            code=code,
            name=name,
            factor_name=self.name,
            score=score,
            detail=f"热度: {hot_score:.0f}"
        )


class ConceptFactor(BaseFactor):
    """题材因子"""

    def __init__(self):
        super().__init__(
            name="concept",
            description="题材因子 - 评估股票的题材热度",
            weight=0.15
        )

    def calculate(self, stock_data: dict) -> Optional[FactorResult]:
        code = stock_data.get("code", "")
        name = stock_data.get("name", "")
        concept_tags = stock_data.get("concept_tags", [])

        if not code:
            return None

        # 题材数量越多，分数越高
        score = min(100, len(concept_tags) * 30)

        return FactorResult(
            code=code,
            name=name,
            factor_name=self.name,
            score=score,
            detail=f"题材: {', '.join(concept_tags[:3])}"
        )


class BoardFactor(BaseFactor):
    """连板因子"""

    def __init__(self):
        super().__init__(
            name="board",
            description="连板因子 - 评估股票的连板高度",
            weight=0.20
        )

    def calculate(self, stock_data: dict) -> Optional[FactorResult]:
        code = stock_data.get("code", "")
        name = stock_data.get("name", "")
        popularity_tag = stock_data.get("popularity_tag", "")

        if not code:
            return None

        # 解析连板高度
        board_num = 0
        if popularity_tag and "板" in popularity_tag:
            try:
                board_num = int(popularity_tag[0])
            except:
                pass

        # 连板高度越高，分数越高
        score = min(100, board_num * 20)

        return FactorResult(
            code=code,
            name=name,
            factor_name=self.name,
            score=score,
            detail=f"连板: {popularity_tag}"
        )


class ReasonFactor(BaseFactor):
    """驱动因子"""

    def __init__(self):
        super().__init__(
            name="reason",
            description="驱动因子 - 评估股票的驱动因素",
            weight=0.10
        )

    def calculate(self, stock_data: dict) -> Optional[FactorResult]:
        code = stock_data.get("code", "")
        name = stock_data.get("name", "")
        reason = stock_data.get("reason", "")

        if not code:
            return None

        # 有明确驱动因素得分高
        score = 80 if reason else 40

        return FactorResult(
            code=code,
            name=name,
            factor_name=self.name,
            score=score,
            detail=f"驱动: {reason[:50]}" if reason else "无明确驱动"
        )
