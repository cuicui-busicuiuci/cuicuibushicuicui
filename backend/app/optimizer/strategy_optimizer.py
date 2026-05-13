from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime
from app.strategies.manager import strategy_manager
from app.backtest.engine import backtest_engine
from app.datasources.ths_hot_source import fetch_ths_hot


@dataclass
class OptimizationResult:
    strategy_name: str
    original_weight: float
    new_weight: float
    performance: Dict
    reason: str


class StrategyOptimizer:
    """策略优化器"""

    def __init__(self):
        self.performance_history: Dict[str, List[Dict]] = {}

    def optimize(self) -> List[OptimizationResult]:
        """优化所有策略"""
        hot_stocks = fetch_ths_hot()
        if not hot_stocks:
            return []

        results = []
        for strategy in strategy_manager.strategies:
            # 运行策略
            signals = strategy_manager.run_strategy(strategy.name, hot_stocks)

            if not signals:
                continue

            # 转换为回测格式
            signal_dicts = [
                {
                    "code": s.code,
                    "name": s.name,
                    "price": s.price,
                    "stop_loss": s.stop_loss,
                    "target_price": s.target_price,
                    "strategy": s.strategy,
                    "reason": s.reason,
                }
                for s in signals
            ]

            # 运行回测
            backtest_result = backtest_engine.run(signal_dicts, {})

            # 计算新权重
            new_weight = self._calculate_new_weight(strategy.name, backtest_result)

            results.append(OptimizationResult(
                strategy_name=strategy.name,
                original_weight=1.0,
                new_weight=new_weight,
                performance={
                    "total_return": backtest_result.total_return,
                    "win_rate": backtest_result.win_rate,
                    "sharpe_ratio": backtest_result.sharpe_ratio,
                    "max_drawdown": backtest_result.max_drawdown,
                    "total_trades": backtest_result.total_trades
                },
                reason=self._generate_reason(backtest_result)
            ))

        return results

    def _calculate_new_weight(self, strategy_name: str, backtest_result) -> float:
        """计算新权重"""
        # 基于回测结果调整权重
        score = 0

        # 胜率权重
        if backtest_result.win_rate > 60:
            score += 30
        elif backtest_result.win_rate > 50:
            score += 20
        else:
            score += 10

        # 夏普比率权重
        if backtest_result.sharpe_ratio > 2:
            score += 30
        elif backtest_result.sharpe_ratio > 1:
            score += 20
        else:
            score += 10

        # 最大回撤权重
        if backtest_result.max_drawdown < 10:
            score += 20
        elif backtest_result.max_drawdown < 20:
            score += 15
        else:
            score += 5

        # 交易次数权重
        if backtest_result.total_trades > 50:
            score += 20
        elif backtest_result.total_trades > 20:
            score += 15
        else:
            score += 5

        # 归一化到0.5-1.5
        return 0.5 + (score / 100)

    def _generate_reason(self, backtest_result) -> str:
        """生成优化原因"""
        reasons = []

        if backtest_result.win_rate > 60:
            reasons.append("胜率优秀")
        elif backtest_result.win_rate > 50:
            reasons.append("胜率良好")
        else:
            reasons.append("胜率一般")

        if backtest_result.sharpe_ratio > 2:
            reasons.append("夏普比率优秀")
        elif backtest_result.sharpe_ratio > 1:
            reasons.append("夏普比率良好")
        else:
            reasons.append("夏普比率一般")

        if backtest_result.max_drawdown < 10:
            reasons.append("回撤控制优秀")
        elif backtest_result.max_drawdown < 20:
            reasons.append("回撤控制良好")
        else:
            reasons.append("回撤较大")

        return "，".join(reasons)

    def get_optimization_report(self) -> Dict:
        """获取优化报告"""
        results = self.optimize()

        report = {
            "timestamp": datetime.now().isoformat(),
            "strategies": [],
            "summary": {
                "total_strategies": len(results),
                "optimized_strategies": sum(1 for r in results if r.new_weight != 1.0),
                "avg_weight": sum(r.new_weight for r in results) / len(results) if results else 0
            }
        }

        for result in results:
            report["strategies"].append({
                "name": result.strategy_name,
                "original_weight": result.original_weight,
                "new_weight": round(result.new_weight, 2),
                "performance": result.performance,
                "reason": result.reason
            })

        return report


strategy_optimizer = StrategyOptimizer()
