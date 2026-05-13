from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime


@dataclass
class NewsAnalysis:
    title: str
    sentiment: str  # positive/negative/neutral
    bullish_score: float  # 0-100
    bearish_score: float  # 0-100
    hot_score: float  # 0-100
    credibility: float  # 0-100
    impact_period: str  # short/medium/long
    related_sectors: List[str]
    related_stocks: List[str]
    keywords: List[str]


class NewsAnalyzer:
    """新闻分析器"""

    def __init__(self):
        # 利好关键词
        self.bullish_keywords = [
            "利好", "增长", "突破", "创新高", "涨停", "强势", "龙头",
            "订单", "合同", "中标", "合作", "战略", "布局", "扩张",
            "业绩预增", "净利润增长", "营收增长", "超预期", "景气度"
        ]

        # 利空关键词
        self.bearish_keywords = [
            "利空", "下跌", "跌停", "亏损", "下滑", "风险", "警示",
            "减持", "质押", "违规", "处罚", "诉讼", "退市", "ST",
            "业绩预减", "净利润下降", "营收下降", "不及预期", "产能过剩"
        ]

        # 板块关键词映射
        self.sector_keywords = {
            "半导体": ["芯片", "半导体", "集成电路", "晶圆", "封测", "光刻"],
            "人工智能": ["AI", "人工智能", "大模型", "算力", "GPU", "数据中心"],
            "新能源": ["光伏", "风电", "储能", "锂电池", "新能源", "碳中和"],
            "医药": ["医药", "生物", "创新药", "医疗器械", "疫苗", "CXO"],
            "消费": ["消费", "白酒", "食品", "家电", "零售", "电商"],
            "金融": ["银行", "券商", "保险", "金融", "证券"],
            "地产": ["地产", "房地产", "物业", "建筑"],
        }

    def analyze(self, title: str, content: str = "") -> NewsAnalysis:
        """分析单条新闻"""
        text = f"{title} {content}"

        # 计算利好分数
        bullish_score = self._calculate_bullish_score(text)

        # 计算利空分数
        bearish_score = self._calculate_bearish_score(text)

        # 判断情绪
        if bullish_score > bearish_score + 20:
            sentiment = "positive"
        elif bearish_score > bullish_score + 20:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        # 计算热度
        hot_score = self._calculate_hot_score(text)

        # 计算可信度
        credibility = self._calculate_credibility(text)

        # 判断影响周期
        impact_period = self._determine_impact_period(text)

        # 提取相关板块
        related_sectors = self._extract_sectors(text)

        # 提取关键词
        keywords = self._extract_keywords(text)

        return NewsAnalysis(
            title=title,
            sentiment=sentiment,
            bullish_score=bullish_score,
            bearish_score=bearish_score,
            hot_score=hot_score,
            credibility=credibility,
            impact_period=impact_period,
            related_sectors=related_sectors,
            related_stocks=[],
            keywords=keywords
        )

    def analyze_batch(self, news_list: List[Dict]) -> List[Dict]:
        """批量分析新闻"""
        results = []
        for news in news_list:
            title = news.get("title", "")
            content = news.get("content", "")
            analysis = self.analyze(title, content)
            results.append({
                "title": title,
                "sentiment": analysis.sentiment,
                "bullish_score": analysis.bullish_score,
                "bearish_score": analysis.bearish_score,
                "hot_score": analysis.hot_score,
                "credibility": analysis.credibility,
                "impact_period": analysis.impact_period,
                "related_sectors": analysis.related_sectors,
                "keywords": analysis.keywords
            })
        return results

    def _calculate_bullish_score(self, text: str) -> float:
        """计算利好分数"""
        count = sum(1 for kw in self.bullish_keywords if kw in text)
        return min(100, count * 15)

    def _calculate_bearish_score(self, text: str) -> float:
        """计算利空分数"""
        count = sum(1 for kw in self.bearish_keywords if kw in text)
        return min(100, count * 15)

    def _calculate_hot_score(self, text: str) -> float:
        """计算热度分数"""
        # 根据关键词数量和类型计算热度
        score = 50
        if any(kw in text for kw in ["涨停", "跌停", "暴涨", "暴跌"]):
            score += 30
        if any(kw in text for kw in ["龙头", "强势", "热点"]):
            score += 20
        return min(100, score)

    def _calculate_credibility(self, text: str) -> float:
        """计算可信度"""
        score = 70
        if any(kw in text for kw in ["公告", "年报", "季报", "官方"]):
            score += 20
        if any(kw in text for kw in ["据", "消息", "报道称"]):
            score += 10
        return min(100, score)

    def _determine_impact_period(self, text: str) -> str:
        """判断影响周期"""
        if any(kw in text for kw in ["战略", "长期", "布局", "五年"]):
            return "long"
        elif any(kw in text for kw in ["季度", "半年", "年度"]):
            return "medium"
        else:
            return "short"

    def _extract_sectors(self, text: str) -> List[str]:
        """提取相关板块"""
        sectors = []
        for sector, keywords in self.sector_keywords.items():
            if any(kw in text for kw in keywords):
                sectors.append(sector)
        return sectors

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        keywords = []
        all_keywords = self.bullish_keywords + self.bearish_keywords
        for kw in all_keywords:
            if kw in text:
                keywords.append(kw)
        return keywords[:5]


news_analyzer = NewsAnalyzer()
