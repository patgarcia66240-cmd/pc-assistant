"""Configuration management"""
import re
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from dotenv import load_dotenv
import os
from pathlib import Path

# Chemin exposé pour que d'autres modules (ex: plugins/config/router.py, plugins/messaging/
# router.py) puissent persister des valeurs dans le même fichier .env que celui chargé ici,
# sans le recalculer ailleurs.
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)


def write_env_value(key: str, value, env_path: Path = ENV_PATH) -> None:
    """Met à jour (ou ajoute) une ligne KEY=value dans un fichier .env, sans toucher au reste.

    Partagé par plugins/config (préférences ARIA) et plugins/messaging (secrets/listes
    blanches WhatsApp/Telegram) — auparavant dupliqué dans plugins/config/router.py. Un
    `env_path` différent du .env du backend est accepté pour pouvoir écrire aussi dans
    whatsapp-bridge/.env (process Node.js séparé, voir plugins/messaging/router.py), qui doit
    garder EXACTEMENT le même WHATSAPP_BRIDGE_SECRET que ce backend."""
    safe_value = str(value).replace("\r", " ").replace("\n", " ")
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    pattern = re.compile(rf"^{re.escape(key)}=")
    for index, line in enumerate(lines):
        if pattern.match(line):
            lines[index] = f"{key}={safe_value}"
            break
    else:
        lines.append(f"{key}={safe_value}")
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

# Chemin absolu (même principe que KINGS_DB_PATH dans kings_service.py) : avec un chemin relatif
# "./pc_assistant.db", le fichier de DB réellement utilisé dépend du dossier depuis lequel le
# process est lancé (uvicorn direct, gunicorn, desktop/main.rs...) — constaté en pratique : deux
# pc_assistant.db différents et désynchronisés existaient (un à la racine du repo, un dans
# backend/). Seule la valeur PAR DÉFAUT est ainsi rendue absolue ; un DATABASE_URL fourni via .env
# (y compris pour une autre base que SQLite) n'est pas touché.
_DEFAULT_DB_PATH = (Path(__file__).resolve().parent / "pc_assistant.db").as_posix()
_DEFAULT_KOKORO_DIR = Path(__file__).resolve().parent / "data" / "tts"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_PATH, extra="ignore")
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_BASE_URL: str = os.getenv("CLAUDE_BASE_URL", "https://api.anthropic.com")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "anthropic")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    OPENAI_IMAGE_MODEL: str = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_BASE_URL: str = os.getenv(
        "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
    )
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "")
    QWEN_BASE_URL: str = os.getenv(
        "QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    )
    QWEN_MODEL: str = os.getenv("QWEN_MODEL", "qwen-plus")
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
    KOKORO_MODEL_PATH: str = os.getenv(
        "KOKORO_MODEL_PATH", str(_DEFAULT_KOKORO_DIR / "kokoro-v1.0.onnx")
    )
    KOKORO_VOICES_PATH: str = os.getenv(
        "KOKORO_VOICES_PATH", str(_DEFAULT_KOKORO_DIR / "voices-v1.0.bin")
    )
    KOKORO_VOICE: str = os.getenv("KOKORO_VOICE", "ff_siwis")
    PIPER_MODEL_PATH: str = os.getenv(
        "PIPER_MODEL_PATH", str(_DEFAULT_KOKORO_DIR / "fr_FR-siwis-medium.onnx")
    )
    PIPER_CONFIG_PATH: str = os.getenv(
        "PIPER_CONFIG_PATH", str(_DEFAULT_KOKORO_DIR / "fr_FR-siwis-medium.onnx.json")
    )
    PIPER_USE_CUDA: bool = os.getenv("PIPER_USE_CUDA", "false").lower() in {"1", "true", "yes"}
    # Coordonnées par défaut : Saint-Martin-de-Crau (13310), utilisées pour la météo/lever-coucher
    # du soleil de la carte Saint du jour. Vérifiées le 10/09/2026 (coordonneesgps.net +
    # infobox Wikipedia, valeurs cohérentes à ~1km près). Redéfinissable via .env si besoin.
    USER_LATITUDE: float = float(os.getenv("USER_LATITUDE", "43.6408"))
    USER_LONGITUDE: float = float(os.getenv("USER_LONGITUDE", "4.8133"))
    USER_CITY_LABEL: str = os.getenv("USER_CITY_LABEL", "Saint-Martin-de-Crau")
    USER_COUNTRY: str = os.getenv("USER_COUNTRY", "France")
    # Identifiants OAuth Google Agenda (projet Google Cloud à créer par l'utilisatrice — voir
    # instructions de configuration fournies séparément). Vides par défaut : l'onglet Agenda le
    # détecte et affiche un état "non configuré" plutôt que d'échouer silencieusement.
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_CALENDAR_REDIRECT_URI: str = os.getenv(
        "GOOGLE_CALENDAR_REDIRECT_URI", "http://127.0.0.1:8000/api/calendar/oauth/callback"
    )
    # Pont WhatsApp (backend/plugins/whatsapp/, voir whatsapp-bridge/ à la racine du repo) : un
    # service Node.js séparé (Baileys, non officiel) qui parle à WhatsApp et relaie les messages
    # ici via POST /api/whatsapp/incoming. WHATSAPP_BRIDGE_SECRET protège cet échange (le pont et
    # ce backend doivent avoir exactement la même valeur, voir whatsapp-bridge/.env) — sans elle
    # le plugin refuse toute requête (503). WHATSAPP_ALLOWED_NUMBERS est vide par défaut : tant
    # qu'aucun numéro n'y est ajouté, ARIA ignore tous les messages WhatsApp entrants (pour ne
    # jamais répondre à un inconnu qui aurait trouvé le numéro dédié).
    WHATSAPP_BRIDGE_URL: str = os.getenv("WHATSAPP_BRIDGE_URL", "http://127.0.0.1:3001")
    WHATSAPP_BRIDGE_SECRET: str = os.getenv("WHATSAPP_BRIDGE_SECRET", "")
    WHATSAPP_ALLOWED_NUMBERS: str = os.getenv("WHATSAPP_ALLOWED_NUMBERS", "")
    # Bot Telegram (backend/telegram_bot.py, script séparé lancé à côté de main.py + voir
    # backend/plugins/telegram/) : API officielle Telegram, gratuite, contrairement à WhatsApp —
    # token créé une fois via @BotFather sur Telegram (aucune approbation, aucun coût). Beaucoup
    # plus simple que le pont WhatsApp : pas de service Node.js séparé à faire tourner en
    # permanence, telegram_bot.py interroge directement POST /api/telegram/incoming et attend la
    # réponse (pas de webhook retour). Mêmes principes de sécurité : TELEGRAM_BRIDGE_SECRET
    # (identique dans backend/.env, lu par les deux côtés puisque c'est le même process Python) et
    # TELEGRAM_ALLOWED_USER_IDS (identifiants Telegram numériques, vide par défaut = aucun message
    # traité).
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_BRIDGE_SECRET: str = os.getenv("TELEGRAM_BRIDGE_SECRET", "")
    TELEGRAM_ALLOWED_USER_IDS: str = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
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
