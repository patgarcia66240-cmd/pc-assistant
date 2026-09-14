"""Persistance de l'appairage avec le téléphone Android (hôte/port/jeton).

Même principe que plugin_loader.STATE_PATH ou messaging (secrets dans backend/.env) : un
petit fichier JSON dans backend/data/, en dehors de backend/plugins/ pour ne pas être
redémarré par le reload de uvicorn (voir plugins/messaging/lifecycle.py, LOG_DIR, pour le bug
déjà rencontré avec un fichier réécrit souvent dans backend/). Le jeton est un secret
d'appairage local (réseau LAN uniquement, jamais exposé sur Internet) : il reste en clair
dans ce fichier, comme WHATSAPP_BRIDGE_SECRET dans backend/.env — backend/data/ est déjà
exclu de Git par .gitignore.
"""
import json
import logging
from pathlib import Path
from typing import Optional, TypedDict

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "android_bridge.json"


class PairingConfig(TypedDict):
    host: str
    port: int
    token: str


def load_config() -> Optional[PairingConfig]:
    if not CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        logger.warning("android_bridge.json illisible (%s), appairage oublié", error)
        return None
    if not all(key in data for key in ("host", "port", "token")):
        return None
    return data


def save_config(host: str, port: int, token: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps({"host": host, "port": port, "token": token}, ensure_ascii=False),
        encoding="utf-8",
    )


def clear_config() -> None:
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()
