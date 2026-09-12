"""Pont Telegram : reçoit les messages du script backend/telegram_bot.py (bot Telegram officiel,
lancé séparément de main.py — voir ce fichier pour la procédure). Contrairement au pont WhatsApp
(backend/plugins/whatsapp/), pas de service à appeler en retour : telegram_bot.py attend
directement la réponse de POST /incoming et la poste lui-même sur Telegram.

Même traitement que le chat normal (voir routes/chat.py — heure/météo, bourse, rois de France,
agenda IA, Claude en dernier recours) et mêmes deux couches de sécurité que le plugin whatsapp :
  1. TELEGRAM_BRIDGE_SECRET : secret partagé (même process Python, mais protège quand même contre
     un autre programme local qui appellerait cette route directement).
  2. TELEGRAM_ALLOWED_USER_IDS : liste blanche d'identifiants Telegram numériques. Vide par
     défaut = aucun message traité, même avec le secret correct.
"""
import json
import logging
import secrets as secrets_module
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import dotenv_values
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from config import ENV_PATH, settings
from routes.chat import chat as core_chat, ChatMessage
from security import require_api_key

TELEGRAM_API_BASE = "https://api.telegram.org"

router = APIRouter()
logger = logging.getLogger(__name__)

# Même fichier que celui écrit par backend/telegram_bot.py (_write_heartbeat) — voir ce script
# pour le détail. HEARTBEAT_STALE_AFTER_SECONDS > l'intervalle d'écriture (30s) pour tolérer un
# passage manqué sans faire clignoter le statut à "hors ligne" pour rien.
STATUS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "telegram_status.json"
HEARTBEAT_STALE_AFTER_SECONDS = 90

# Carnet des personnes ayant déjà écrit au bot — ajouté le 12/09/2026, pendant du carnet
# importable côté WhatsApp (voir plugins/whatsapp/router.py GET /contacts), mais construit très
# différemment : un bot Telegram n'a PAS accès à un répertoire (contrairement à Baileys, qui
# simule un vrai appareil lié et reçoit une vraie synchronisation des contacts du téléphone) —
# l'API Bot ne renvoie que les infos des utilisateurs qui écrivent. Rempli au fil de l'eau par
# _remember_user, appelé depuis /incoming ci-dessous à chaque message d'un utilisateur autorisé.
KNOWN_USERS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "telegram_known_users.json"


def _load_known_users() -> dict:
    if not KNOWN_USERS_PATH.exists():
        return {}
    try:
        return json.loads(KNOWN_USERS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        logger.warning("[ARIA][Telegram] telegram_known_users.json illisible (%s), traité comme vide", error)
        return {}


def _remember_user(user_id: str, name: str | None) -> None:
    if not name:
        return
    users = _load_known_users()
    if users.get(user_id, {}).get("name") == name:
        return  # déjà à jour : pas la peine de réécrire le fichier à chaque message reçu
    users[user_id] = {"id": user_id, "name": name}
    KNOWN_USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    KNOWN_USERS_PATH.write_text(json.dumps(users, indent=2, ensure_ascii=False), encoding="utf-8")


class IncomingMessage(BaseModel):
    user_id: str
    message: str
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


class SendMessage(BaseModel):
    to: str  # identifiant Telegram numérique du destinataire
    message: str


def _allowed_user_ids() -> set[str]:
    return {n.strip() for n in settings.TELEGRAM_ALLOWED_USER_IDS.split(",") if n.strip()}


async def _verify_bridge_secret(x_bridge_secret: str | None = Header(default=None)) -> None:
    if not settings.TELEGRAM_BRIDGE_SECRET:
        raise HTTPException(status_code=503, detail="TELEGRAM_BRIDGE_SECRET non configuré côté backend")
    if not x_bridge_secret or not secrets_module.compare_digest(x_bridge_secret, settings.TELEGRAM_BRIDGE_SECRET):
        raise HTTPException(status_code=403, detail="Secret de pont invalide")


@router.post("/incoming", dependencies=[Depends(_verify_bridge_secret)])
async def incoming(payload: IncomingMessage):
    if payload.user_id not in _allowed_user_ids():
        logger.warning("[ARIA][Telegram] Message ignoré (utilisateur non autorisé) : %s", payload.user_id)
        return {"response": "Ce bot est privé, désolée."}

    display_name = " ".join(part for part in (payload.first_name, payload.last_name) if part) or payload.username
    _remember_user(payload.user_id, display_name)

    # conversation_id dérivé de l'identifiant Telegram : chaque utilisateur autorisé garde son
    # propre historique (table conversations), séparé des conversations démarrées depuis l'app —
    # même principe que le pont WhatsApp (voir plugins/whatsapp/router.py).
    chat_message = ChatMessage(
        message=payload.message,
        context={},
        conversation_id=f"telegram:{payload.user_id}",
    )
    try:
        result = await core_chat(chat_message)
        return {"response": result.get("response") or "…"}
    except HTTPException as error:
        logger.error("[ARIA][Telegram] Échec du traitement du message de %s : %s", payload.user_id, error.detail)
        return {"response": "Désolée, je n'ai pas pu traiter ce message pour le moment."}


@router.post("/send", dependencies=[Depends(require_api_key)])
async def send(payload: SendMessage):
    """Envoi À LA DEMANDE, depuis l'app — ajouté le 12/09/2026 (voir plugins/messaging/
    chat_handler.py). Contrairement à WhatsApp, pas de passage par telegram_bot.py (process
    séparé, à l'écoute mais pas piloté à distance) : on appelle directement l'API Bot Telegram
    avec TELEGRAM_BOT_TOKEN, la même chose que fait n'importe quel bot Telegram pour envoyer un
    message de sa propre initiative. Contrainte propre à Telegram (pas à ARIA) : le destinataire
    doit avoir déjà démarré une conversation avec ce bot au moins une fois, sinon l'API refuse."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Telegram non configuré (token du bot manquant)")
    if not payload.message.strip():
        raise HTTPException(status_code=422, detail="Message vide")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{TELEGRAM_API_BASE}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": payload.to, "text": payload.message},
            )
            data = response.json()
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"Échec de l'envoi Telegram : {error}") from error
    if not data.get("ok"):
        raise HTTPException(status_code=502, detail=data.get("description", "Échec de l'envoi Telegram"))
    return {"status": "sent", "to": payload.to}


@router.get("/contacts", dependencies=[Depends(require_api_key)])
async def known_contacts():
    """Utilisateurs Telegram déjà connus d'ARIA (ont écrit au bot au moins une fois) — pour
    importer en un clic dans le carnet de plugins/messaging/ (voir contacts.py), comme pour
    WhatsApp. Liste forcément partielle par nature (voir KNOWN_USERS_PATH plus haut) : impossible
    de faire mieux avec l'API Bot Telegram, ce n'est pas une erreur ou un oubli de notre part.
    Différent de POST /api/messaging/telegram-users (ajouté par ailleurs le même jour) : celui-ci
    lit l'historique Telegram (getUpdates) à la demande, celui-ci lit le carnet qu'ARIA construit
    au fil de l'eau à chaque message reçu — les deux sources se complètent, l'une ne remplace pas
    l'autre."""
    users = _load_known_users()
    return {"contacts": sorted(users.values(), key=lambda u: u["name"].lower())}


@router.get("/status", dependencies=[Depends(require_api_key)])
async def status():
    """Diagnostic pour l'onglet Messagerie (frontend) : la config .env est-elle en place, et
    telegram_bot.py (process séparé) a-t-il donné signe de vie récemment ? Contrairement au pont
    WhatsApp, il n'y a pas de service HTTP local à interroger — on lit juste le heartbeat qu'il
    écrit lui-même (voir STATUS_PATH ci-dessus)."""
    if not settings.TELEGRAM_BOT_TOKEN:
        token = str(dotenv_values(ENV_PATH).get("TELEGRAM_BOT_TOKEN") or "").strip()
        if token:
            settings.TELEGRAM_BOT_TOKEN = token

    token_configured = bool(settings.TELEGRAM_BOT_TOKEN)
    secret_configured = bool(settings.TELEGRAM_BRIDGE_SECRET)
    configured = token_configured and secret_configured
    if not configured:
        return {
            "configured": False,
            "token_configured": token_configured,
            "secret_configured": secret_configured,
            "running": False,
        }

    last_seen = None
    bot_username = None
    running = False
    try:
        heartbeat = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        last_seen = heartbeat.get("last_seen")
        bot_username = heartbeat.get("bot_username")
        if last_seen:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(last_seen)).total_seconds()
            running = age < HEARTBEAT_STALE_AFTER_SECONDS
    except FileNotFoundError:
        pass  # telegram_bot.py n'a jamais tourné (ou pas depuis la création de data/)
    except (json.JSONDecodeError, ValueError, OSError) as error:
        logger.warning("[ARIA][Telegram] Heartbeat illisible (%s) : %s", STATUS_PATH, error)

    return {
        "configured": True,
        "allowed_users_configured": bool(settings.TELEGRAM_ALLOWED_USER_IDS.strip()),
        "running": running,
        "last_seen": last_seen,
        "bot_username": bot_username,
    }
