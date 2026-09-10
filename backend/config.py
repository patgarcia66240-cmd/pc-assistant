"""Configuration management"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from dotenv import load_dotenv
import os
from pathlib import Path

# Chemin exposé pour que d'autres modules (ex: routes/config.py) puissent persister des
# valeurs dans le même fichier .env que celui chargé ici, sans le recalculer ailleurs.
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

# Chemin absolu (même principe que KINGS_DB_PATH dans kings_service.py) : avec un chemin relatif
# "./pc_assistant.db", le fichier de DB réellement utilisé dépend du dossier depuis lequel le
# process est lancé (uvicorn direct, gunicorn, desktop/main.rs...) — constaté en pratique : deux
# pc_assistant.db différents et désynchronisés existaient (un à la racine du repo, un dans
# backend/). Seule la valeur PAR DÉFAUT est ainsi rendue absolue ; un DATABASE_URL fourni via .env
# (y compris pour une autre base que SQLite) n'est pas touché.
_DEFAULT_DB_PATH = (Path(__file__).resolve().parent / "pc_assistant.db").as_posix()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_PATH, extra="ignore")
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_BASE_URL: str = os.getenv("CLAUDE_BASE_URL", "https://api.anthropic.com")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
    TWELVE_DATA_API_KEY: str = os.getenv("TWELVE_DATA_API_KEY", "")
    EODHD_API_KEY: str = os.getenv("EODHD_API_KEY", "")
    METAL_SENTINEL_API_KEY: str = os.getenv("METAL_SENTINEL_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}")
    FILES_ROOT: str = os.getenv("FILES_ROOT", os.path.expanduser("~"))
    ARIA_NAME: str = os.getenv("ARIA_NAME", "ARIA")
    ARIA_AVATAR: str = os.getenv("ARIA_AVATAR", "🤖")
    ARIA_LANGUAGE: str = os.getenv("ARIA_LANGUAGE", "fr")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_AUTH_TOKEN: str = os.getenv("API_AUTH_TOKEN", "")
    # Coordonnées par défaut : Saint-Martin-de-Crau (13310), utilisées pour la météo/lever-coucher
    # du soleil de la carte Saint du jour. Vérifiées le 10/09/2026 (coordonneesgps.net +
    # infobox Wikipedia, valeurs cohérentes à ~1km près). Redéfinissable via .env si besoin.
    USER_LATITUDE: float = float(os.getenv("USER_LATITUDE", "43.6408"))
    USER_LONGITUDE: float = float(os.getenv("USER_LONGITUDE", "4.8133"))
    USER_CITY_LABEL: str = os.getenv("USER_CITY_LABEL", "Saint-Martin-de-Crau")
    # Identifiants OAuth Google Agenda (projet Google Cloud à créer par l'utilisatrice — voir
    # instructions de configuration fournies séparément). Vides par défaut : l'onglet Agenda le
    # détecte et affiche un état "non configuré" plutôt que d'échouer silencieusement.
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_CALENDAR_REDIRECT_URI: str = os.getenv(
        "GOOGLE_CALENDAR_REDIRECT_URI", "http://127.0.0.1:8000/api/calendar/oauth/callback"
    )
    DEBUG: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"development", "dev", "debug"}:
                return True
            if normalized in {"release", "production", "prod"}:
                return False
        return value

settings = Settings()
