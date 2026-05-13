from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/{code}")
def get_reports(code: str, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    from app.services.report_service import get_stock_reports

    data = get_stock_reports(code, page, size)
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/search")
def search_reports(q: str = Query(..., description="搜索关键词"), size: int = Query(50, ge=1, le=200)):
    from app.services.report_service import search_reports

    data = search_reports(q, size)
    return {"code": 0, "data": data, "message": "ok"}
