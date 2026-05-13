from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/check/{code}")
def check_stock_risk(code: str):
    from app.risk.manager import risk_manager
    from app.datasources.tencent_source import fetch_tencent_quote

    stock_data = fetch_tencent_quote(code)
    if not stock_data:
        return {"code": 0, "data": None, "message": "无法获取股票数据"}

    result = risk_manager.check_stock(stock_data)
    return {
        "code": 0,
        "data": {
            "code": result.code,
            "name": result.name,
            "risk_level": result.risk_level,
            "risk_factors": result.risk_factors,
            "suggestion": result.suggestion
        },
        "message": "ok"
    }


@router.get("/market")
def get_market_risk():
    from app.risk.manager import risk_manager
    from app.strategies.sentiment import sentiment_model
    from app.datasources.ths_hot_source import fetch_ths_hot

    hot_stocks = fetch_ths_hot()
    sentiment = sentiment_model.analyze(hot_stocks)

    return {
        "code": 0,
        "data": {
            "sentiment": sentiment,
            "risk_level": "HIGH" if sentiment["stage"] in ["高潮期", "退潮期"] else "MEDIUM",
            "suggestion": sentiment["action"]
        },
        "message": "ok"
    }


@router.post("/check-recommendations")
def check_recommendations_risk():
    from app.risk.manager import risk_manager
    from app.recommendation.daily import daily_recommender

    recommendations = daily_recommender.generate()
    checked = risk_manager.check_recommendations(recommendations.get("recommendations", []))

    return {
        "code": 0,
        "data": {
            "date": recommendations.get("date"),
            "recommendations": checked,
            "total": len(checked),
            "blocked": sum(1 for r in checked if r.get("risk_level") == "BLOCK"),
            "high_risk": sum(1 for r in checked if r.get("risk_level") == "HIGH")
        },
        "message": "ok"
    }
