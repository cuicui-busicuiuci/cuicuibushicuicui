from fastapi import APIRouter

router = APIRouter()


@router.get("/{code}")
def get_valuation(code: str):
    from app.services.valuation_service import full_valuation

    data = full_valuation(code)
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/compare")
def compare_valuation(codes: str):
    from app.services.valuation_service import batch_valuation

    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    data = batch_valuation(code_list)
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/forecast/{code}")
def get_forecast(code: str):
    from app.services.valuation_service import get_consensus_forecast

    data = get_consensus_forecast(code)
    return {"code": 0, "data": data, "message": "ok"}
