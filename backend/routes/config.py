"""Configuration routes"""
from fastapi import APIRouter
from pydantic import BaseModel
from config import settings

router = APIRouter()

class AriaConfig(BaseModel):
    name: str
    avatar: str
    language: str

@router.get("/aria")
async def get_aria_config():
    """Get ARIA configuration"""
    return {
        "name": settings.ARIA_NAME,
        "avatar": settings.ARIA_AVATAR,
        "language": settings.ARIA_LANGUAGE
    }

@router.put("/aria")
async def update_aria_config(config: AriaConfig):
    """Update ARIA configuration"""
    settings.ARIA_NAME = config.name
    settings.ARIA_AVATAR = config.avatar
    settings.ARIA_LANGUAGE = config.language
    return {"status": "updated", "config": config.model_dump()}
