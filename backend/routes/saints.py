"""Daily saint routes."""
from fastapi import APIRouter
from services.saint_service import get_daily_events, get_saint_of_day

router = APIRouter()


@router.get("/today")
async def saint_of_day():
    result = get_saint_of_day()
    result["observances"] = await get_daily_events()
    return result