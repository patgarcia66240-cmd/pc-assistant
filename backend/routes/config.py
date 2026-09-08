"""Configuration routes"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/aria")
async def get_aria_config():
    """Get ARIA configuration"""
    return {
        "name": "ARIA",
        "avatar": "🤖",
        "language": "fr"
    }

@router.put("/aria")
async def update_aria_config(config: dict):
    """Update ARIA configuration"""
    return {"status": "updated", "config": config}
