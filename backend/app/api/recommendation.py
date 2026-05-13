from fastapi import APIRouter

router = APIRouter()


@router.get("/today")
def get_today_recommendations():
    from app.recommendation.daily import daily_recommender
    data = daily_recommender.generate()
    return {"code": 0, "data": data, "message": "ok"}
