from typing import List, Dict
from datetime import date


class SentimentModel:
    """情绪周期模型"""

    def __init__(self):
        self.stages = {
            "冰点期": {
                "description": "市场极度悲观，跌停数量多，涨停数量少",
                "action": "等待转机",
                "position": 0,
                "risk_level": "LOW"
            },
            "回暖期": {
                "description": "市场开始回暖，涨停数量增加，跌停减少",
                "action": "小仓位试错",
                "position": 30,
                "risk_level": "MEDIUM"
            },
            "上升期": {
                "description": "市场情绪高涨，涨停数量多，连板高度增加",
                "action": "积极参与",
                "position": 60,
                "risk_level": "MEDIUM"
            },
            "高潮期": {
                "description": "市场极度亢奋，涨停数量暴增，炸板率低",
                "action": "注意风险",
                "position": 80,
                "risk_level": "HIGH"
            },
            "退潮期": {
                "description": "市场开始回落，涨停数量减少，炸板率上升",
                "action": "降低仓位",
                "position": 20,
                "risk_level": "HIGH"
            },
        }

    def analyze(self, hot_stocks: List[Dict]) -> Dict:
        """分析市场情绪"""
        if not hot_stocks:
            return {"stage": "未知", "score": 0, "description": "无数据"}

        # 统计涨停数量
        limit_up_count = sum(1 for s in hot_stocks if s.get("change_pct", 0) >= 9.9)

        # 统计跌停数量
        limit_down_count = sum(1 for s in hot_stocks if s.get("change_pct", 0) <= -9.9)

        # 统计连板高度
        max_board = 0
        board_counts = {}
        for s in hot_stocks:
            tag = s.get("popularity_tag", "")
            if "板" in tag:
                try:
                    board_num = int(tag[0])
                    max_board = max(max_board, board_num)
                    board_counts[board_num] = board_counts.get(board_num, 0) + 1
                except:
                    pass

        # 统计首板数量
        first_board_count = board_counts.get(1, 0)

        # 统计二板数量
        second_board_count = board_counts.get(2, 0)

        # 统计高标股数量（3板以上）
        high_board_count = sum(count for board, count in board_counts.items() if board >= 3)

        # 计算情绪分数
        score = 0
        score += min(limit_up_count * 1.5, 30)  # 涨停数量贡献最多30分
        score += min(max_board * 8, 25)  # 连板高度贡献最多25分
        score += min(first_board_count * 2, 15)  # 首板数量贡献最多15分
        score += min(second_board_count * 3, 15)  # 二板数量贡献最多15分
        score += min(high_board_count * 5, 15)  # 高标股贡献最多15分

        # 计算赚钱效应
        profit_effect = self._calculate_profit_effect(hot_stocks)

        # 计算市场情绪指标
        sentiment_index = self._calculate_sentiment_index(
            limit_up_count, limit_down_count, max_board, first_board_count
        )

        # 判断情绪阶段
        if score >= 80:
            stage = "高潮期"
        elif score >= 60:
            stage = "上升期"
        elif score >= 40:
            stage = "回暖期"
        elif score >= 20:
            stage = "冰点期"
        else:
            stage = "退潮期"

        return {
            "stage": stage,
            "score": round(score, 1),
            "limit_up_count": limit_up_count,
            "limit_down_count": limit_down_count,
            "max_board": max_board,
            "first_board_count": first_board_count,
            "second_board_count": second_board_count,
            "high_board_count": high_board_count,
            "hot_count": len(hot_stocks),
            "profit_effect": profit_effect,
            "sentiment_index": sentiment_index,
            "description": self.stages[stage]["description"],
            "action": self.stages[stage]["action"],
            "suggested_position": self.stages[stage]["position"],
            "risk_level": self.stages[stage]["risk_level"]
        }

    def _calculate_profit_effect(self, hot_stocks: List[Dict]) -> float:
        """计算赚钱效应"""
        if not hot_stocks:
            return 0

        # 计算平均涨幅
        avg_change = sum(s.get("change_pct", 0) for s in hot_stocks) / len(hot_stocks)

        # 计算涨停占比
        limit_up_count = sum(1 for s in hot_stocks if s.get("change_pct", 0) >= 9.9)
        limit_up_ratio = limit_up_count / len(hot_stocks) * 100

        # 赚钱效应 = 平均涨幅 * 0.6 + 涨停占比 * 0.4
        profit_effect = avg_change * 0.6 + limit_up_ratio * 0.4

        return round(profit_effect, 2)

    def _calculate_sentiment_index(self, limit_up, limit_down, max_board, first_board) -> float:
        """计算情绪指数"""
        # 涨跌停比
        if limit_down == 0:
            limit_ratio = limit_up
        else:
            limit_ratio = limit_up / limit_down

        # 连板高度指数
        board_index = max_board * 10

        # 首板活跃度
        first_board_index = first_board * 2

        # 综合情绪指数
        sentiment_index = limit_ratio * 0.4 + board_index * 0.3 + first_board_index * 0.3

        return round(sentiment_index, 2)

    def get_trading_suggestion(self, sentiment: Dict) -> Dict:
        """获取交易建议"""
        stage = sentiment.get("stage", "未知")
        score = sentiment.get("score", 0)

        if stage == "高潮期":
            return {
                "suggestion": "市场情绪极度亢奋，建议注意风险",
                "position": 30,
                "strategy": "防守为主，关注龙头股",
                "risk": "高位股风险大，避免追高"
            }
        elif stage == "上升期":
            return {
                "suggestion": "市场情绪向好，可以积极参与",
                "position": 60,
                "strategy": "进攻为主，关注热点板块",
                "risk": "注意板块轮动风险"
            }
        elif stage == "回暖期":
            return {
                "suggestion": "市场开始回暖，可以小仓位试错",
                "position": 40,
                "strategy": "试错为主，关注首板股",
                "risk": "控制仓位，设好止损"
            }
        elif stage == "冰点期":
            return {
                "suggestion": "市场情绪低迷，建议观望",
                "position": 10,
                "strategy": "观望为主，等待机会",
                "risk": "避免盲目抄底"
            }
        elif stage == "退潮期":
            return {
                "suggestion": "市场开始回落，建议降低仓位",
                "position": 20,
                "strategy": "防守为主，减少操作",
                "risk": "避免追高，及时止损"
            }
        else:
            return {
                "suggestion": "市场情绪不明，建议观望",
                "position": 0,
                "strategy": "观望为主",
                "risk": "等待市场明朗"
            }


sentiment_model = SentimentModel()
