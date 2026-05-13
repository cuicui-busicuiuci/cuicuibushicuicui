from typing import List, Dict
from dataclasses import dataclass


@dataclass
class MoneyFlow:
    code: str
    name: str
    net_inflow: float  # 净流入
    main_inflow: float  # 主力流入
    retail_inflow: float  # 散户流入
    flow_score: float
    flow_type: str  # 主力流入/散户流入/资金流出


class MoneyFlowAnalyzer:
    """资金流分析模型"""

    def __init__(self):
        self.flow_types = {
            "主力流入": "主力资金大幅流入，看涨信号",
            "散户流入": "散户资金流入，谨慎追高",
            "资金流出": "资金流出，注意风险"
        }

    def analyze(self, hot_stocks: List[Dict]) -> List[MoneyFlow]:
        """分析资金流"""
        if not hot_stocks:
            return []

        flows = []

        for stock in hot_stocks:
            code = stock.get("code", "")
            name = stock.get("name", "")
            change_pct = stock.get("change_pct", 0)
            hot_score = stock.get("hot_score", 0)
            concept_tags = stock.get("concept_tags", [])

            if not code:
                continue

            # 模拟资金流数据（实际应该从数据源获取）
            net_inflow = self._simulate_net_inflow(change_pct, hot_score)
            main_inflow = self._simulate_main_inflow(change_pct, hot_score)
            retail_inflow = net_inflow - main_inflow

            # 计算资金流分数
            flow_score = self._calculate_flow_score(net_inflow, main_inflow)

            # 判断资金流类型
            flow_type = self._determine_flow_type(net_inflow, main_inflow)

            flows.append(MoneyFlow(
                code=code,
                name=name,
                net_inflow=net_inflow,
                main_inflow=main_inflow,
                retail_inflow=retail_inflow,
                flow_score=flow_score,
                flow_type=flow_type
            ))

        # 按资金流分数排序
        flows.sort(key=lambda x: x.flow_score, reverse=True)

        return flows

    def _simulate_net_inflow(self, change_pct: float, hot_score: float) -> float:
        """模拟净流入（实际应该从数据源获取）"""
        # 涨幅越大，净流入越多
        base = change_pct * 1000
        # 热度越高，净流入越多
        hot_bonus = hot_score / 10000
        return round(base + hot_bonus, 2)

    def _simulate_main_inflow(self, change_pct: float, hot_score: float) -> float:
        """模拟主力流入（实际应该从数据源获取）"""
        # 涨幅越大，主力流入越多
        base = change_pct * 500
        # 热度越高，主力流入越多
        hot_bonus = hot_score / 20000
        return round(base + hot_bonus, 2)

    def _calculate_flow_score(self, net_inflow: float, main_inflow: float) -> float:
        """计算资金流分数"""
        score = 0

        # 净流入贡献
        if net_inflow > 0:
            score += min(net_inflow / 1000, 40)
        else:
            score -= min(abs(net_inflow) / 1000, 20)

        # 主力流入贡献
        if main_inflow > 0:
            score += min(main_inflow / 500, 40)
        else:
            score -= min(abs(main_inflow) / 500, 20)

        # 归一化到0-100
        score = max(0, min(100, score + 50))

        return round(score, 2)

    def _determine_flow_type(self, net_inflow: float, main_inflow: float) -> str:
        """判断资金流类型"""
        if net_inflow <= 0:
            return "资金流出"
        elif main_inflow > net_inflow * 0.6:
            return "主力流入"
        else:
            return "散户流入"

    def get_flow_analysis(self, flow: MoneyFlow) -> Dict:
        """获取资金流分析"""
        analysis = {
            "code": flow.code,
            "name": flow.name,
            "flow_type": flow.flow_type,
            "flow_score": flow.flow_score,
            "net_inflow": flow.net_inflow,
            "main_inflow": flow.main_inflow,
            "retail_inflow": flow.retail_inflow,
            "strength": self._evaluate_strength(flow),
            "suggestion": self._generate_suggestion(flow)
        }

        return analysis

    def _evaluate_strength(self, flow: MoneyFlow) -> str:
        """评估强度"""
        if flow.flow_score >= 80:
            return "极强"
        elif flow.flow_score >= 60:
            return "强"
        elif flow.flow_score >= 40:
            return "中"
        else:
            return "弱"

    def _generate_suggestion(self, flow: MoneyFlow) -> str:
        """生成建议"""
        if flow.flow_type == "主力流入":
            if flow.flow_score >= 70:
                return "主力大幅流入，可重点关注"
            else:
                return "主力小幅流入，可关注"
        elif flow.flow_type == "散户流入":
            return "散户流入为主，谨慎追高"
        else:
            return "资金流出，注意风险"


money_flow_analyzer = MoneyFlowAnalyzer()
