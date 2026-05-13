from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class FactorResult:
    code: str
    name: str
    factor_name: str
    score: float  # 0-100
    detail: str


class BaseFactor(ABC):
    def __init__(self, name: str, description: str, weight: float = 1.0):
        self.name = name
        self.description = description
        self.weight = weight

    @abstractmethod
    def calculate(self, stock_data: dict) -> Optional[FactorResult]:
        """计算因子分数"""
        pass

    def normalize(self, value: float, min_val: float, max_val: float) -> float:
        """归一化到0-100"""
        if max_val == min_val:
            return 50
        return max(0, min(100, (value - min_val) / (max_val - min_val) * 100))
