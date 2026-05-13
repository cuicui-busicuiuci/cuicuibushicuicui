from dataclasses import dataclass
from typing import List, Dict, Optional
from app.strategies.sentiment import sentiment_model
from app.datasources.ths_hot_source import fetch_ths_hot


@dataclass
class RiskCheck:
    code: str
    name: str
    risk_level: str  # LOW/MEDIUM/HIGH/BLOCK
    risk_factors: List[str]
    suggestion: str


class RiskManager:
    """风控管理器"""

    def __init__(self):
        self.block_keywords = ["ST", "*ST", "退市"]
        self.high_risk_keywords = ["高位", "炸板", "滞涨"]

    def check_stock(self, stock_data: Dict) -> RiskCheck:
        """检查单只股票风险"""
        code = stock_data.get("code", "")
        name = stock_data.get("name", "")
        change_pct = stock_data.get("change_pct", 0)
        popularity_tag = stock_data.get("popularity_tag", "")
        reason = stock_data.get("reason", "")

        risk_factors = []
        risk_level = "LOW"

        # 1. ST股一票否决
        if any(kw in name for kw in self.block_keywords):
            return RiskCheck(
                code=code,
                name=name,
                risk_level="BLOCK",
                risk_factors=["ST股，禁止推荐"],
                suggestion="ST股存在退市风险，不建议操作"
            )

        # 2. 连续大涨风险
        if change_pct and change_pct > 15:
            risk_factors.append(f"近期涨幅过大: {change_pct:.2f}%")
            risk_level = "HIGH"

        # 3. 高位风险
        if popularity_tag and "板" in popularity_tag:
            try:
                board_num = int(popularity_tag[0])
                if board_num >= 5:
                    risk_factors.append(f"连板过高: {popularity_tag}")
                    risk_level = "HIGH"
            except:
                pass

        # 4. 炸板风险
        if "炸板" in reason or "打开" in reason:
            risk_factors.append("存在炸板风险")
            risk_level = max(risk_level, "MEDIUM")

        # 5. 涨幅适中
        if change_pct and 5 < change_pct < 10:
            risk_level = min(risk_level, "MEDIUM")

        if not risk_factors:
            risk_factors.append("无明显风险")

        suggestion = self._generate_suggestion(risk_level, risk_factors)

        return RiskCheck(
            code=code,
            name=name,
            risk_level=risk_level,
            risk_factors=risk_factors,
            suggestion=suggestion
        )

    def check_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
        """检查推荐列表的风险"""
        hot_stocks = fetch_ths_hot()
        sentiment = sentiment_model.analyze(hot_stocks)

        checked = []
        for rec in recommendations:
            risk = self.check_stock(rec)
            rec["risk_level"] = risk.risk_level
            rec["risk_factors"] = risk.risk_factors
            rec["risk_suggestion"] = risk.suggestion

            # 根据市场情绪调整
            if sentiment["stage"] in ["退潮期", "冰点期"]:
                rec["risk_level"] = "HIGH"
                rec["risk_factors"].append("市场情绪低迷，建议观望")

            checked.append(rec)

        return checked

    def _generate_suggestion(self, risk_level: str, risk_factors: List[str]) -> str:
        """生成风险建议"""
        if risk_level == "BLOCK":
            return "存在重大风险，禁止操作"
        elif risk_level == "HIGH":
            return "风险较高，建议观望或小仓位参与"
        elif risk_level == "MEDIUM":
            return "风险适中，注意止损"
        else:
            return "风险较低，可正常参与"


risk_manager = RiskManager()
