from typing import List, Optional
from app.strategies.base import BaseStrategy, Signal
from app.strategies.leader import LeaderStrategy
from app.strategies.first_board import FirstBoardStrategy
from app.strategies.weak_to_strong import WeakToStrongStrategy
from app.strategies.money_flow import MoneyFlowStrategy
from app.strategies.second_board import SecondBoardStrategy
from app.strategies.leader_dip import LeaderDipStrategy
from app.strategies.main_wave import MainWaveStrategy


class StrategyManager:
    def __init__(self):
        self.strategies: List[BaseStrategy] = []
        self._load_default_strategies()

    def _load_default_strategies(self):
        self.strategies = [
            LeaderStrategy(),
            FirstBoardStrategy(),
            WeakToStrongStrategy(),
            MoneyFlowStrategy(),
            SecondBoardStrategy(),
            LeaderDipStrategy(),
            MainWaveStrategy(),
        ]

    def add_strategy(self, strategy: BaseStrategy):
        self.strategies.append(strategy)

    def run_all(self, stock_data_list: List[dict]) -> List[Signal]:
        signals = []
        for stock_data in stock_data_list:
            for strategy in self.strategies:
                signal = strategy.check_conditions(stock_data)
                if signal:
                    signals.append(signal)
        return signals

    def run_strategy(self, strategy_name: str, stock_data_list: List[dict]) -> List[Signal]:
        strategy = self.get_strategy(strategy_name)
        if not strategy:
            return []

        signals = []
        for stock_data in stock_data_list:
            signal = strategy.check_conditions(stock_data)
            if signal:
                signals.append(signal)
        return signals

    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        for strategy in self.strategies:
            if strategy.name == name:
                return strategy
        return None

    def list_strategies(self) -> List[dict]:
        return [
            {"name": s.name, "description": s.description}
            for s in self.strategies
        ]


strategy_manager = StrategyManager()
