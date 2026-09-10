"""Configuration routes"""
import re
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from config import settings, ENV_PATH
from security import require_api_key

router = APIRouter()

class AriaConfig(BaseModel):
    name: str
    avatar: str
    language: str

def _write_env_value(key: str, value: str) -> None:
    """Met à jour (ou ajoute) une ligne KEY=value dans le fichier .env, sans toucher au
    reste (clés API, DATABASE_URL, etc.). Nécessaire pour que la config ARIA survive à un
    redémarrage du backend (avant, elle ne vivait qu'en mémoire dans `settings`)."""
    safe_value = str(value).replace("\r", " ").replace("\n", " ")
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    pattern = re.compile(rf"^{re.escape(key)}=")
    for index, line in enumerate(lines):
        if pattern.match(line):
            lines[index] = f"{key}={safe_value}"
            break
    else:
        lines.append(f"{key}={safe_value}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

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
    settings.ARIA_LANGUAGE = config.language
    _write_env_value("ARIA_NAME", config.name)
    _write_env_value("ARIA_AVATAR", config.avatar)
    _write_env_value("ARIA_LANGUAGE", config.language)
    return {"status": "updated", "config": config.model_dump()}
