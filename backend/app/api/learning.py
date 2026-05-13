from fastapi import APIRouter, Query

router = APIRouter()


@router.post("/run")
def run_learning():
    from app.learning.self_learning import self_learning_system
    report = self_learning_system.generate_learning_report()
    return {"code": 0, "data": report, "message": "ok"}


@router.get("/report")
def get_learning_report():
    from app.learning.self_learning import self_learning_system
    report = self_learning_system.generate_learning_report()
    return {"code": 0, "data": report, "message": "ok"}


@router.get("/performance")
def get_performance(days: int = Query(30, ge=1, le=365)):
    from app.learning.self_learning import self_learning_system
    performance = self_learning_system.analyze_performance(days)
    return {"code": 0, "data": performance, "message": "ok"}


@router.post("/track")
def track_recommendation(
    code: str = Query(..., description="股票代码"),
    strategy: str = Query(..., description="策略名称"),
    price: float = Query(..., description="推荐价格")
):
    from app.learning.self_learning import self_learning_system
    self_learning_system.track_recommendation({
        "code": code,
        "strategy": strategy,
        "price": price
    })
    return {"code": 0, "data": {"message": "已跟踪"}, "message": "ok"}


@router.post("/update-result")
def update_result(
    code: str = Query(..., description="股票代码"),
    profit_pct: float = Query(..., description="收益百分比")
):
    from app.learning.self_learning import self_learning_system
    self_learning_system.update_recommendation_result(code, {
        "profit_pct": profit_pct,
        "updated_at": "now"
    })
    return {"code": 0, "data": {"message": "已更新"}, "message": "ok"}
