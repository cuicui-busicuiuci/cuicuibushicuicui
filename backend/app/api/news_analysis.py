from fastapi import APIRouter, Query

router = APIRouter()


@router.post("/analyze")
def analyze_news(title: str = Query(..., description="新闻标题"), content: str = Query("", description="新闻内容")):
    from app.news_analysis.analyzer import news_analyzer
    result = news_analyzer.analyze(title, content)
    return {
        "code": 0,
        "data": {
            "title": result.title,
            "sentiment": result.sentiment,
            "bullish_score": result.bullish_score,
            "bearish_score": result.bearish_score,
            "hot_score": result.hot_score,
            "credibility": result.credibility,
            "impact_period": result.impact_period,
            "related_sectors": result.related_sectors,
            "keywords": result.keywords
        },
        "message": "ok"
    }


@router.get("/hot")
def get_hot_news():
    from app.datasources.akshare_source import fetch_cls_news
    from app.news_analysis.analyzer import news_analyzer

    news_list = fetch_cls_news(50)
    if not news_list:
        return {"code": 0, "data": [], "message": "无新闻数据"}

    analyzed = news_analyzer.analyze_batch(news_list)

    # 按热度排序
    analyzed.sort(key=lambda x: x["hot_score"], reverse=True)

    return {"code": 0, "data": analyzed[:20], "message": "ok"}


@router.get("/sentiment")
def get_news_sentiment():
    from app.datasources.akshare_source import fetch_cls_news
    from app.news_analysis.analyzer import news_analyzer

    news_list = fetch_cls_news(100)
    if not news_list:
        return {"code": 0, "data": None, "message": "无新闻数据"}

    analyzed = news_analyzer.analyze_batch(news_list)

    # 统计情绪分布
    positive_count = sum(1 for n in analyzed if n["sentiment"] == "positive")
    negative_count = sum(1 for n in analyzed if n["sentiment"] == "negative")
    neutral_count = sum(1 for n in analyzed if n["sentiment"] == "neutral")

    total = len(analyzed)
    avg_bullish = sum(n["bullish_score"] for n in analyzed) / total
    avg_bearish = sum(n["bearish_score"] for n in analyzed) / total

    # 提取热门板块
    sector_counts = {}
    for n in analyzed:
        for sector in n["related_sectors"]:
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

    hot_sectors = sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "code": 0,
        "data": {
            "total_news": total,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "avg_bullish_score": round(avg_bullish, 2),
            "avg_bearish_score": round(avg_bearish, 2),
            "hot_sectors": [{"name": s[0], "count": s[1]} for s in hot_sectors]
        },
        "message": "ok"
    }
