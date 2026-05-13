from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class LeaderStock:
    code: str
    name: str
    board_count: int
    hot_score: float
    change_pct: float
    concept_tags: List[str]
    reason: str
    leader_score: float
    leader_type: str  # 连板龙头/板块龙头/人气龙头


class LeaderIdentifier:
    """龙头识别模型"""

    def __init__(self):
        self.leader_types = {
            "连板龙头": "连续涨停，高度最高",
            "板块龙头": "板块内涨幅最大，带动效应强",
            "人气龙头": "热度最高，市场关注度大"
        }

    def identify(self, hot_stocks: List[Dict]) -> List[LeaderStock]:
        """识别龙头股"""
        if not hot_stocks:
            return []

        leaders = []

        for stock in hot_stocks:
            code = stock.get("code", "")
            name = stock.get("name", "")
            change_pct = stock.get("change_pct", 0)
            hot_score = stock.get("hot_score", 0)
            concept_tags = stock.get("concept_tags", [])
            popularity_tag = stock.get("popularity_tag", "")
            reason = stock.get("reason", "")

            if not code:
                continue

            # 计算连板数
            board_count = self._extract_board_count(popularity_tag)

            # 计算龙头分数
            leader_score = self._calculate_leader_score(
                board_count, hot_score, change_pct, concept_tags
            )

            # 判断龙头类型
            leader_type = self._determine_leader_type(
                board_count, hot_score, change_pct
            )

            # 只有分数大于50的才算龙头
            if leader_score >= 50:
                leaders.append(LeaderStock(
                    code=code,
                    name=name,
                    board_count=board_count,
                    hot_score=hot_score,
                    change_pct=change_pct,
                    concept_tags=concept_tags,
                    reason=reason,
                    leader_score=leader_score,
                    leader_type=leader_type
                ))

        # 按龙头分数排序
        leaders.sort(key=lambda x: x.leader_score, reverse=True)

        return leaders

    def _extract_board_count(self, popularity_tag: str) -> int:
        """提取连板数"""
        if not popularity_tag:
            return 0

        if "板" in popularity_tag:
            try:
                # 提取数字部分
                num_str = ""
                for char in popularity_tag:
                    if char.isdigit():
                        num_str += char
                    else:
                        break
                if num_str:
                    return int(num_str)
            except:
                pass

        return 0

    def _calculate_leader_score(self, board_count: int, hot_score: float,
                                 change_pct: float, concept_tags: List[str]) -> float:
        """计算龙头分数"""
        score = 0

        # 连板高度贡献（最高40分）
        score += min(board_count * 10, 40)

        # 热度贡献（最高30分）
        score += min(hot_score / 30000, 30)

        # 涨幅贡献（最高20分）
        if change_pct >= 9.9:
            score += 20
        elif change_pct >= 5:
            score += 15
        elif change_pct >= 3:
            score += 10

        # 题材贡献（最高10分）
        score += min(len(concept_tags) * 3, 10)

        return round(score, 2)

    def _determine_leader_type(self, board_count: int, hot_score: float,
                                change_pct: float) -> str:
        """判断龙头类型"""
        # 连板龙头：连板数最高
        if board_count >= 3:
            return "连板龙头"

        # 人气龙头：热度最高
        if hot_score > 500000:
            return "人气龙头"

        # 板块龙头：涨幅较大
        if change_pct >= 9.9:
            return "板块龙头"

        return "普通强势股"

    def get_leader_analysis(self, leader: LeaderStock) -> Dict:
        """获取龙头分析"""
        analysis = {
            "code": leader.code,
            "name": leader.name,
            "leader_type": leader.leader_type,
            "leader_score": leader.leader_score,
            "strength": self._evaluate_strength(leader),
            "risk": self._evaluate_risk(leader),
            "suggestion": self._generate_suggestion(leader)
        }

        return analysis

    def _evaluate_strength(self, leader: LeaderStock) -> str:
        """评估强度"""
        if leader.leader_score >= 80:
            return "极强"
        elif leader.leader_score >= 60:
            return "强"
        elif leader.leader_score >= 40:
            return "中"
        else:
            return "弱"

    def _evaluate_risk(self, leader: LeaderStock) -> str:
        """评估风险"""
        if leader.board_count >= 5:
            return "高位风险大"
        elif leader.board_count >= 3:
            return "有一定风险"
        else:
            return "风险可控"

    def _generate_suggestion(self, leader: LeaderStock) -> str:
        """生成建议"""
        if leader.leader_type == "连板龙头":
            if leader.board_count >= 5:
                return "高位龙头，谨慎追高"
            else:
                return "连板龙头，可关注"
        elif leader.leader_type == "人气龙头":
            return "人气龙头，可关注回调机会"
        elif leader.leader_type == "板块龙头":
            return "板块龙头，可关注"
        else:
            return "强势股，可关注"


leader_identifier = LeaderIdentifier()
