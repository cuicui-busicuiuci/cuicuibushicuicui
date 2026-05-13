from fastapi import APIRouter

router = APIRouter()


@router.get("/leaders")
def get_leaders():
    from app.models.leader import leader_identifier
    from app.datasources.ths_hot_source import fetch_ths_hot

    hot_stocks = fetch_ths_hot()
    leaders = leader_identifier.identify(hot_stocks)

    result = [
        {
            "code": l.code,
            "name": l.name,
            "board_count": l.board_count,
            "hot_score": l.hot_score,
            "change_pct": l.change_pct,
            "concept_tags": l.concept_tags,
            "reason": l.reason,
            "leader_score": l.leader_score,
            "leader_type": l.leader_type
        }
        for l in leaders[:20]
    ]

    return {"code": 0, "data": result, "message": "ok"}


@router.get("/leaders/{code}")
def get_leader_analysis(code: str):
    from app.models.leader import leader_identifier
    from app.datasources.ths_hot_source import fetch_ths_hot

    hot_stocks = fetch_ths_hot()
    leaders = leader_identifier.identify(hot_stocks)

    leader = next((l for l in leaders if l.code == code), None)
    if not leader:
        return {"code": 0, "data": None, "message": "未找到龙头股"}

    analysis = leader_identifier.get_leader_analysis(leader)
    return {"code": 0, "data": analysis, "message": "ok"}


@router.get("/money-flow")
def get_money_flow():
    from app.models.money_flow import money_flow_analyzer
    from app.datasources.ths_hot_source import fetch_ths_hot

    hot_stocks = fetch_ths_hot()
    flows = money_flow_analyzer.analyze(hot_stocks)

    result = [
        {
            "code": f.code,
            "name": f.name,
            "net_inflow": f.net_inflow,
            "main_inflow": f.main_inflow,
            "retail_inflow": f.retail_inflow,
            "flow_score": f.flow_score,
            "flow_type": f.flow_type
        }
        for f in flows[:20]
    ]

    return {"code": 0, "data": result, "message": "ok"}


@router.get("/money-flow/{code}")
def get_money_flow_analysis(code: str):
    from app.models.money_flow import money_flow_analyzer
    from app.datasources.ths_hot_source import fetch_ths_hot

    hot_stocks = fetch_ths_hot()
    flows = money_flow_analyzer.analyze(hot_stocks)

    flow = next((f for f in flows if f.code == code), None)
    if not flow:
        return {"code": 0, "data": None, "message": "未找到资金流数据"}

    analysis = money_flow_analyzer.get_flow_analysis(flow)
    return {"code": 0, "data": analysis, "message": "ok"}


@router.get("/sentiment")
def get_sentiment_detail():
    from app.strategies.sentiment import sentiment_model
    from app.datasources.ths_hot_source import fetch_ths_hot

    hot_stocks = fetch_ths_hot()
    sentiment = sentiment_model.analyze(hot_stocks)
    trading_suggestion = sentiment_model.get_trading_suggestion(sentiment)

    return {
        "code": 0,
        "data": {
            "sentiment": sentiment,
            "trading_suggestion": trading_suggestion
        },
        "message": "ok"
    }
