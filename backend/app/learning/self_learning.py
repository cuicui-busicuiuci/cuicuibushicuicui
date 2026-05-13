from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime, timedelta
from app.strategies.manager import strategy_manager
from app.factors.manager import factor_manager
from app.backtest.engine import backtest_engine
from app.datasources.ths_hot_source import fetch_ths_hot


@dataclass
class LearningResult:
    strategy_name: str
    original_weight: float
    new_weight: float
    performance: Dict
    improvement: str


class SelfLearningSystem:
    """自学习升级系统"""

    def __init__(self):
        self.recommendation_history: List[Dict] = []
        self.performance_history: Dict[str, List[Dict]] = {}
        self.learning_logs: List[Dict] = []

    def track_recommendation(self, recommendation: Dict):
        """跟踪推荐结果"""
        self.recommendation_history.append({
            **recommendation,
            "tracked_at": datetime.now().isoformat(),
            "result": None  # 待填充实际结果
        })

    def update_recommendation_result(self, code: str, result: Dict):
        """更新推荐结果"""
        for rec in self.recommendation_history:
            if rec.get("code") == code and rec.get("result") is None:
                rec["result"] = result
                rec["updated_at"] = datetime.now().isoformat()
                break

    def analyze_performance(self, days: int = 30) -> Dict:
        """分析推荐表现"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_recs = [
            r for r in self.recommendation_history
            if r.get("tracked_at") and datetime.fromisoformat(r["tracked_at"]) > cutoff_date
        ]

        if not recent_recs:
            return {"error": "无推荐历史数据"}

        # 统计各策略表现
        strategy_performance = {}
        for rec in recent_recs:
            strategy = rec.get("strategy", "unknown")
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {
                    "total": 0,
                    "success": 0,
                    "total_return": 0,
                    "avg_return": 0
                }

            result = rec.get("result")
            if result:
                strategy_performance[strategy]["total"] += 1
                if result.get("profit_pct", 0) > 0:
                    strategy_performance[strategy]["success"] += 1
                strategy_performance[strategy]["total_return"] += result.get("profit_pct", 0)

        # 计算平均收益
        for strategy in strategy_performance:
            total = strategy_performance[strategy]["total"]
            if total > 0:
                strategy_performance[strategy]["avg_return"] = (
                    strategy_performance[strategy]["total_return"] / total
                )
                strategy_performance[strategy]["win_rate"] = (
                    strategy_performance[strategy]["success"] / total * 100
                )

        return {
            "period_days": days,
            "total_recommendations": len(recent_recs),
            "strategy_performance": strategy_performance
        }

    def optimize_strategies(self) -> List[LearningResult]:
        """优化策略权重"""
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
            new_weight = self._calculate_optimized_weight(strategy.name, backtest_result)

            # 记录学习日志
            self.learning_logs.append({
                "strategy": strategy.name,
                "timestamp": datetime.now().isoformat(),
                "performance": {
                    "total_return": backtest_result.total_return,
                    "win_rate": backtest_result.win_rate,
                    "sharpe_ratio": backtest_result.sharpe_ratio
                },
                "new_weight": new_weight
            })

            results.append(LearningResult(
                strategy_name=strategy.name,
                original_weight=1.0,
                new_weight=new_weight,
                performance={
                    "total_return": backtest_result.total_return,
                    "win_rate": backtest_result.win_rate,
                    "sharpe_ratio": backtest_result.sharpe_ratio
                },
                improvement=self._generate_improvement_text(backtest_result)
            ))

        return results

    def _calculate_optimized_weight(self, strategy_name: str, backtest_result) -> float:
        """计算优化后的权重"""
        score = 50  # 基础分

        # 胜率贡献
        if backtest_result.win_rate > 70:
            score += 25
        elif backtest_result.win_rate > 60:
            score += 15
        elif backtest_result.win_rate > 50:
            score += 5
        else:
            score -= 10

        # 夏普比率贡献
        if backtest_result.sharpe_ratio > 3:
            score += 25
        elif backtest_result.sharpe_ratio > 2:
            score += 15
        elif backtest_result.sharpe_ratio > 1:
            score += 5
        else:
            score -= 10

        # 最大回撤贡献
        if backtest_result.max_drawdown < 5:
            score += 15
        elif backtest_result.max_drawdown < 10:
            score += 10
        elif backtest_result.max_drawdown < 15:
            score += 5
        else:
            score -= 5

        # 归一化到0.5-1.5
        return 0.5 + (score / 100)

    def _generate_improvement_text(self, backtest_result) -> str:
        """生成改进说明"""
        improvements = []

        if backtest_result.win_rate > 60:
            improvements.append("胜率优秀")
        elif backtest_result.win_rate > 50:
            improvements.append("胜率良好")
        else:
            improvements.append("胜率需提升")

        if backtest_result.sharpe_ratio > 2:
            improvements.append("风险收益比优秀")
        elif backtest_result.sharpe_ratio > 1:
            improvements.append("风险收益比良好")
        else:
            improvements.append("风险收益比需优化")

        return "，".join(improvements)

    def generate_learning_report(self) -> Dict:
        """生成学习报告"""
        # 分析最近30天表现
        performance = self.analyze_performance(30)

        # 优化策略
        optimizations = self.optimize_strategies()

        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "performance_analysis": performance,
            "strategy_optimizations": [
                {
                    "strategy": o.strategy_name,
                    "original_weight": o.original_weight,
                    "new_weight": round(o.new_weight, 2),
                    "performance": o.performance,
                    "improvement": o.improvement
                }
                for o in optimizations
            ],
            "learning_logs": self.learning_logs[-10:],  # 最近10条日志
            "recommendations": self._generate_recommendations(optimizations)
        }

        return report

    def _generate_recommendations(self, optimizations: List[LearningResult]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        for opt in optimizations:
            if opt.new_weight > 1.2:
                recommendations.append(f"策略 {opt.strategy_name} 表现优秀，建议增加权重")
            elif opt.new_weight < 0.8:
                recommendations.append(f"策略 {opt.strategy_name} 表现不佳，建议降低权重或调整参数")
            else:
                recommendations.append(f"策略 {opt.strategy_name} 表现稳定，保持当前权重")

        return recommendations


self_learning_system = SelfLearningSystem()
