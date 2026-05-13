from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/quote/{code}")
def get_quote(code: str, source: str = Query("cache", pattern="^(realtime|cache)$")):
    from app.services.market_service import get_stock_quote

    data = get_stock_quote(code, force_realtime=source == "realtime")
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/quotes")
def get_quotes(codes: str = Query(..., description="逗号分隔的股票代码")):
    from app.services.market_service import get_batch_quotes

    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    data = get_batch_quotes(code_list)
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/kline/{code}")
def get_kline(
    code: str,
    category: int = Query(4, description="4=日线,5=周线,6=月线,7=1分,8=5分"),
    limit: int = Query(100, ge=1, le=500),
):
    from app.services.market_service import get_kline

    data = get_kline(code, category, limit)
    return {"code": 0, "data": data, "message": "ok"}
