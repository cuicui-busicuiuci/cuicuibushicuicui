from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/list")
def list_factors():
    from app.factors.manager import factor_manager
    data = [
        {
            "name": f.name,
            "description": f.description,
            "weight": f.weight
        }
        for f in factor_manager.factors
    ]
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/calculate/{code}")
def calculate_factors(code: str):
    from app.factors.manager import factor_manager
    from app.datasources.tencent_source import fetch_tencent_quote
    from app.datasources.ths_hot_source import fetch_ths_hot

    # 获取股票数据
    quote = fetch_tencent_quote(code)
    if not quote:
        return {"code": 0, "data": None, "message": "无法获取股票数据"}

    # 合并热点数据
    hot_stocks = fetch_ths_hot()
    hot_data = next((s for s in hot_stocks if s.get("code") == code), {})

    stock_data = {**quote, **hot_data}
    result = factor_manager.calculate_all(stock_data)

    return {"code": 0, "data": result, "message": "ok"}


@router.get("/rank")
def get_factor_rank(top: int = Query(20, ge=1, le=100)):
    from app.factors.manager import factor_manager
    from app.datasources.ths_hot_source import fetch_ths_hot

    hot_stocks = fetch_ths_hot()
    if not hot_stocks:
        return {"code": 0, "data": [], "message": "无热点数据"}

    results = factor_manager.get_top_stocks(hot_stocks, top)
    return {"code": 0, "data": results, "message": "ok"}


@router.get("/ai-score")
def get_ai_score(top: int = Query(20, ge=1, le=100)):
    from app.factors.manager import factor_manager
    from app.strategies.manager import strategy_manager
    from app.strategies.sentiment import sentiment_model
    from app.datasources.ths_hot_source import fetch_ths_hot

    hot_stocks = fetch_ths_hot()
    if not hot_stocks:
        return {"code": 0, "data": [], "message": "无热点数据"}

    # 获取市场情绪
    sentiment = sentiment_model.analyze(hot_stocks)

    # 计算因子分数
    factor_results = factor_manager.calculate_batch(hot_stocks)

    # 计算策略信号
    strategy_signals = strategy_manager.run_all(hot_stocks)
    signal_codes = {s.code for s in strategy_signals}

    # 整合AI评分
    ai_scores = []
    for stock in factor_results[:top]:
        code = stock["code"]
        has_signal = code in signal_codes

        # AI综合评分
        factor_score = stock["total_score"]
        strategy_bonus = 20 if has_signal else 0
        sentiment_bonus = 10 if sentiment["score"] > 60 else 0

        total_score = min(100, factor_score + strategy_bonus + sentiment_bonus)

        # 确定等级
        if total_score >= 90:
            level = "强关注"
        elif total_score >= 80:
            level = "重点观察"
        elif total_score >= 70:
            level = "普通观察"
        elif total_score >= 60:
            level = "低优先级"
        else:
            level = "不推荐"

        ai_scores.append({
            "code": code,
            "name": stock["name"],
            "total_score": round(total_score, 2),
            "factor_score": round(factor_score, 2),
            "has_signal": has_signal,
            "level": level,
            "factors": stock["factors"]
        })

    # 按总分排序
    ai_scores.sort(key=lambda x: x["total_score"], reverse=True)

    return {
        "code": 0,
        "data": {
            "market_sentiment": sentiment,
            "stocks": ai_scores
        },
        "message": "ok"
    }
