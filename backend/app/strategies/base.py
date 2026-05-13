from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from datetime import date


@dataclass
class Signal:
    code: str
    name: str
    strategy: str
    signal_type: str  # buy/sell/hold
    price: float
    stop_loss: float
    target_price: float
    reason: str
    risk: str
    confidence: float  # 0-100
    holding_days: int
    created_at: str


@dataclass
class BacktestResult:
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    profit_loss_ratio: float
    avg_holding_days: float
    max_consecutive_loss: int
    total_trades: int


class BaseStrategy(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def check_conditions(self, stock_data: dict) -> Optional[Signal]:
        """检查股票是否满足策略条件"""
        pass

    @abstractmethod
    def get_buy_reason(self, stock_data: dict) -> str:
        """获取买入理由"""
        pass

    @abstractmethod
    def get_risk(self, stock_data: dict) -> str:
        """获取风险提示"""
        pass

    def calculate_stop_loss(self, price: float, pct: float = 0.05) -> float:
        """计算止损价"""
        return round(price * (1 - pct), 2)

    def calculate_target(self, price: float, pct: float = 0.15) -> float:
        """计算目标价"""
        return round(price * (1 + pct), 2)
