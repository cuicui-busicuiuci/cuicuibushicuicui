from typing import List, Dict, Optional
from app.factors.base import BaseFactor, FactorResult
from app.factors.technical import (
    ChangePctFactor,
    HotScoreFactor,
    ConceptFactor,
    BoardFactor,
    ReasonFactor
)


class FactorManager:
    """因子管理器"""

    def __init__(self):
        self.factors: List[BaseFactor] = []
        self._load_default_factors()

    def _load_default_factors(self):
        self.factors = [
            ChangePctFactor(),
            HotScoreFactor(),
            ConceptFactor(),
            BoardFactor(),
            ReasonFactor(),
        ]

    def add_factor(self, factor: BaseFactor):
        self.factors.append(factor)

    def calculate_all(self, stock_data: dict) -> Dict:
        """计算所有因子分数"""
        code = stock_data.get("code", "")
        name = stock_data.get("name", "")

        results = []
        total_score = 0
        total_weight = 0

        for factor in self.factors:
            result = factor.calculate(stock_data)
            if result:
                results.append(result)
                total_score += result.score * factor.weight
                total_weight += factor.weight

        # 计算加权平均分
        avg_score = total_score / total_weight if total_weight > 0 else 0

        return {
            "code": code,
            "name": name,
            "total_score": round(avg_score, 2),
            "factors": [
                {
                    "name": r.factor_name,
                    "score": r.score,
                    "detail": r.detail
                }
                for r in results
            ]
        }

    def calculate_batch(self, stock_data_list: List[Dict]) -> List[Dict]:
        """批量计算因子分数"""
        results = []
        for stock_data in stock_data_list:
            result = self.calculate_all(stock_data)
            results.append(result)

        # 按总分排序
        results.sort(key=lambda x: x["total_score"], reverse=True)
        return results

    def get_top_stocks(self, stock_data_list: List[Dict], top_n: int = 10) -> List[Dict]:
        """获取因子分数最高的股票"""
        results = self.calculate_batch(stock_data_list)
        return results[:top_n]


factor_manager = FactorManager()
