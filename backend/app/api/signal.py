from fastapi import APIRouter, Query
from datetime import date

router = APIRouter()


@router.get("/hot")
def get_hot_stocks(date: str = Query(default_factory=lambda: date.today().isoformat())):
    from app.datasources.ths_hot_source import fetch_ths_hot
    data = fetch_ths_hot(date)
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/hot/topics")
def get_hot_topics(
    date: str = Query(default_factory=lambda: date.today().isoformat()),
    top: int = Query(10, ge=1, le=50),
):
    from app.datasources.ths_hot_source import fetch_ths_hot
    from collections import Counter

    hot_stocks = fetch_ths_hot(date)
    reasons = []
    for stock in hot_stocks:
        reason = stock.get("reason", "")
        if reason:
            tags = [t.strip() for t in reason.replace("，", ",").split(",") if t.strip()]
            reasons.extend(tags)

    counter = Counter(reasons)
    data = [{"topic": topic, "count": count} for topic, count in counter.most_common(top)]
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/north")
def get_north_flow():
    from app.datasources.ths_north_source import fetch_north_realtime
    data = fetch_north_realtime()
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/north/history")
def get_north_history(type: str = Query("hgt", pattern="^(hgt|sgt|all)$")):
    from app.datasources.ths_north_source import fetch_north_history
    data = fetch_north_history()
    return {"code": 0, "data": data, "message": "ok"}
