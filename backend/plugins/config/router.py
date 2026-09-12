"""Configuration routes"""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from config import settings, write_env_value
from security import require_api_key
from services.local_service import country_code, geocoding_city_name
from services.claude_service import claude_service

router = APIRouter()

class AriaConfig(BaseModel):
    name: str
    avatar: str
    language: Literal["fr"] = "fr"


class AppPreferences(BaseModel):
    country: str = Field(min_length=2, max_length=80)
    city: str = Field(min_length=1, max_length=120)
    ai_provider: Literal["anthropic", "openai", "gemini", "qwen"]
    ai_model: str = Field(min_length=1, max_length=120)
    ai_api_key: str | None = Field(default=None, max_length=500)


PROVIDER_SETTINGS = {
    "anthropic": ("CLAUDE_API_KEY", "CLAUDE_MODEL"),
    "openai": ("OPENAI_API_KEY", "OPENAI_MODEL"),
    "gemini": ("GEMINI_API_KEY", "GEMINI_MODEL"),
    "qwen": ("QWEN_API_KEY", "QWEN_MODEL"),
}


def _provider_preferences(provider: str) -> tuple[str, bool]:
    key_setting, model_setting = PROVIDER_SETTINGS[provider]
    return getattr(settings, model_setting), bool(getattr(settings, key_setting))


def _provider_catalog() -> dict:
    return {
        provider: {
            "model": _provider_preferences(provider)[0],
            "api_key_configured": _provider_preferences(provider)[1],
        }
        for provider in PROVIDER_SETTINGS
    }


async def _geocode_location(city: str, country: str) -> dict:
    code = country_code(country)
    if not code:
        raise HTTPException(status_code=422, detail="Pays non reconnu")
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={
                    "name": geocoding_city_name(city),
                    "count": 1,
                    "language": "fr",
                    "format": "json",
                    "countryCode": code,
                },
            )
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail="Service de localisation indisponible") from error

    try:
        places = response.json().get("results", [])
    except (ValueError, AttributeError) as error:
        raise HTTPException(status_code=502, detail="Réponse de localisation invalide") from error
    if not places:
        raise HTTPException(status_code=422, detail="Ville introuvable dans le pays sélectionné")
    return places[0]


@router.get("/aria", dependencies=[Depends(require_api_key)])
async def get_aria_config():
    """Get ARIA configuration"""
    return {
        "name": settings.ARIA_NAME,
        "avatar": settings.ARIA_AVATAR,
        "language": settings.ARIA_LANGUAGE
    }

@router.put("/aria", dependencies=[Depends(require_api_key)])
async def update_aria_config(config: AriaConfig):
    """Update ARIA configuration (mémoire + persistance dans .env)"""
    settings.ARIA_NAME = config.name
    settings.ARIA_AVATAR = config.avatar
    settings.ARIA_LANGUAGE = "fr"
    write_env_value("ARIA_NAME", config.name)
    write_env_value("ARIA_AVATAR", config.avatar)
    write_env_value("ARIA_LANGUAGE", "fr")
    return {"status": "updated", "config": {**config.model_dump(), "language": "fr"}}


@router.get("/preferences", dependencies=[Depends(require_api_key)])
async def get_app_preferences():
    model, api_key_configured = _provider_preferences(settings.AI_PROVIDER)
    return {
        "country": settings.USER_COUNTRY,
        "city": settings.USER_CITY_LABEL,
        "ai_provider": settings.AI_PROVIDER,
        "ai_model": model,
        "ai_api_key": "",
        "ai_api_key_configured": api_key_configured,
        "ai_providers": _provider_catalog(),
    }


@router.put("/preferences", dependencies=[Depends(require_api_key)])
async def update_app_preferences(preferences: AppPreferences):
    place = await _geocode_location(preferences.city.strip(), preferences.country.strip())
    city = place.get("name") or preferences.city.strip()
    try:
        latitude = float(place["latitude"])
        longitude = float(place["longitude"])
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=502, detail="Coordonnées de localisation invalides") from error

    settings.USER_COUNTRY = preferences.country.strip()
    settings.USER_CITY_LABEL = city
    settings.USER_LATITUDE = latitude
    settings.USER_LONGITUDE = longitude
    settings.AI_PROVIDER = preferences.ai_provider
    key_setting, model_setting = PROVIDER_SETTINGS[preferences.ai_provider]
    setattr(settings, model_setting, preferences.ai_model.strip())
    if preferences.ai_api_key and preferences.ai_api_key.strip():
        setattr(settings, key_setting, preferences.ai_api_key.strip())
        write_env_value(key_setting, preferences.ai_api_key.strip())
    if preferences.ai_provider == "anthropic":
        claude_service.refresh_anthropic_client()

    persisted = {
        "USER_COUNTRY": settings.USER_COUNTRY,
        "USER_CITY_LABEL": settings.USER_CITY_LABEL,
        "USER_LATITUDE": latitude,
        "USER_LONGITUDE": longitude,
        "AI_PROVIDER": settings.AI_PROVIDER,
        model_setting: preferences.ai_model.strip(),
    }
    for key, value in persisted.items():
        write_env_value(key, value)

    return {
        "status": "updated",
        "preferences": {
            "country": settings.USER_COUNTRY,
            "city": settings.USER_CITY_LABEL,
            "ai_provider": settings.AI_PROVIDER,
            "ai_model": getattr(settings, model_setting),
            "ai_api_key": "",
            "ai_api_key_configured": bool(getattr(settings, key_setting)),
            "ai_providers": _provider_catalog(),
        },
    }
