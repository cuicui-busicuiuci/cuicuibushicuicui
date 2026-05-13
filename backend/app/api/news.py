from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/{code}")
def get_stock_news(code: str, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    from app.services.news_service import get_stock_news

    data = get_stock_news(code, page, size)
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/cls")
def get_cls_news(limit: int = Query(50, ge=1, le=200)):
    from app.services.news_service import get_cls_flash

    data = get_cls_flash(limit)
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/global")
def get_global_news(limit: int = Query(50, ge=1, le=200)):
    from app.services.news_service import get_global_news

    data = get_global_news(limit)
    return {"code": 0, "data": data, "message": "ok"}
