"""Configuration des ponts de messagerie (WhatsApp, Telegram) depuis l'onglet Messagerie —
ajouté le 12/09/2026 suite à un retour de Sarah : avant, activer whatsapp/telegram voulait dire
éditer backend/.env (et whatsapp-bridge/.env) à la main, un redémarrage à l'aveugle, puis
espérer que ça marche. Ce routeur permet de le faire depuis l'app.

Volontairement séparé de backend/plugins/whatsapp/router.py et backend/plugins/telegram/
router.py : CE routeur, celui de "messaging", doit rester joignable même quand les plugins
whatsapp/telegram sont encore désactivés (c'est justement le cas qu'on configure !) — il est
monté tant que le plugin "messaging" est actif, ce qui est vrai par défaut
(enabled_by_default: true, indépendant de whatsapp/telegram).

Ce que fait chaque route "-config" :
  1. Valide et persiste les valeurs saisies dans backend/.env (write_env_value, voir config.py).
  2. Génère un secret de pont si aucun n'existe encore (l'utilisatrice n'a jamais besoin de le
     voir ni de le choisir elle-même) — et, pour WhatsApp UNIQUEMENT, l'écrit aussi dans
     whatsapp-bridge/.env (process Node.js séparé, qui doit avoir EXACTEMENT le même secret).
     Pas de pendant pour Telegram : telegram_bot.py charge le même backend/.env (voir son
     docstring), un seul fichier suffit.
  3. Active le plugin correspondant (plugin_loader.set_plugin_enabled) — évite un aller-retour
     par l'onglet Plugins.
  4. Lance le process externe correspondant s'il ne tourne pas déjà (voir lifecycle.py),
     ajouté le 12/09/2026 : plus besoin d'ouvrir un terminal séparé après avoir enregistré.

Point important sur le (re)lancement (bug corrigé le 12/09/2026, repéré par Sarah : un simple
changement de numéros autorisés relançait tout le pont whatsapp-bridge/, ce qui coupait une
session WhatsApp déjà liée et forçait un nouveau scan de QR code à chaque enregistrement) :
  - allowed_numbers / allowed_user_ids sont lus en direct par CE process (settings, mis à jour en
    mémoire juste avant l'appel à lifecycle.*), jamais par le pont lui-même — un changement de ces
    listes ne justifie donc JAMAIS de redémarrer whatsapp-bridge/ ou telegram_bot.py. On utilise
    start_*() (ne fait rien s'il tourne déjà), jamais restart_*().
  - Le token du bot Telegram, lui, EST lu une seule fois par telegram_bot.py au lancement
    (Application.builder().token(...)) : un nouveau token ne peut être pris en compte que par un
    vrai redémarrage du process — c'est le seul cas où on appelle restart_telegram_bot().
  - whatsapp-bridge/ n'a pas d'équivalent : son secret n'est écrit qu'une seule fois dans sa vie
    (voir le "if not settings.WHATSAPP_BRIDGE_SECRET" plus bas, jamais régénéré ensuite), donc à
    ce moment-là le pont n'a de toute façon jamais encore été démarré — start_whatsapp_bridge()
    suffit toujours, un restart ne serait jamais utile.

Un redémarrage du BACKEND (pas du pont) reste nécessaire une seule fois, la toute première
activation d'un canal, pour que FastAPI monte le routeur du plugin whatsapp/telegram lui-même
(voir plugin_loader.py, un routeur ne peut pas être ajouté à chaud) — plugin_newly_enabled
ci-dessous indique précisément ce cas, pour ne pas réclamer un redémarrage à chaque enregistrement.
"""
import logging
import re
import secrets as secrets_module
from pathlib import Path

import httpx
from dotenv import dotenv_values
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from config import ENV_PATH, settings, write_env_value
from plugin_loader import list_plugin_status, set_plugin_enabled
from security import require_api_key

from . import contacts as contacts_store
from . import lifecycle

router = APIRouter()
logger = logging.getLogger(__name__)

# backend/plugins/messaging/router.py -> .parent=messaging, .parent.parent=plugins,
# .parent.parent.parent=backend, .parent.parent.parent.parent=racine du repo (contient
# whatsapp-bridge/ en frère de backend/, voir whatsapp-bridge/README.md).
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
WHATSAPP_BRIDGE_ENV_PATH = REPO_ROOT / "whatsapp-bridge" / ".env"

NUMBER_LIST_PATTERN = re.compile(r"^[\d+,\s]*$")
USER_ID_LIST_PATTERN = re.compile(r"^[\d,\s]*$")


def _normalize_list(raw: str) -> str:
    """"33612345678, +33698765432" -> "33612345678,33698765432" : une liste blanche propre,
    sans espaces ni "+", cohérente avec _normalize_number côté plugins/whatsapp/router.py."""
    return ",".join(part.strip().lstrip("+") for part in raw.split(",") if part.strip())


def _is_plugin_enabled(plugin_id: str) -> bool:
    """Utilisé pour savoir SI un plugin était déjà activé avant cet appel (et donc si un
    redémarrage du backend est réellement nécessaire pour que FastAPI monte son routeur) —
    set_plugin_enabled() écrase l'état sans dire s'il a changé, il faut le lire avant."""
    return any(plugin.get("id") == plugin_id and plugin.get("enabled") for plugin in list_plugin_status())


def _reload_telegram_token_from_env() -> None:
    """Recharge seulement le token Telegram après une édition manuelle de backend/.env."""
    if settings.TELEGRAM_BOT_TOKEN:
        return
    token = str(dotenv_values(ENV_PATH).get("TELEGRAM_BOT_TOKEN") or "").strip()
    if token:
        settings.TELEGRAM_BOT_TOKEN = token


class ContactPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    whatsapp: str | None = Field(default=None, max_length=30)
    telegram: str | None = Field(default=None, max_length=30)


class WhatsappConfig(BaseModel):
    allowed_numbers: str = Field(default="", max_length=2000)


class TelegramConfig(BaseModel):
    bot_token: str | None = Field(default=None, max_length=200)
    allowed_user_ids: str = Field(default="", max_length=2000)


class TelegramDiscoveryRequest(BaseModel):
    bot_token: str | None = Field(default=None, max_length=200)


@router.get("/whatsapp-config", dependencies=[Depends(require_api_key)])
async def get_whatsapp_config():
    return {
        "allowed_numbers": settings.WHATSAPP_ALLOWED_NUMBERS,
        "secret_configured": bool(settings.WHATSAPP_BRIDGE_SECRET),
    }


@router.put("/whatsapp-config", dependencies=[Depends(require_api_key)])
async def update_whatsapp_config(payload: WhatsappConfig):
    if not NUMBER_LIST_PATTERN.match(payload.allowed_numbers):
        raise HTTPException(status_code=422, detail="Numéros invalides : chiffres, \"+\" et virgules uniquement")

    allowed_numbers = _normalize_list(payload.allowed_numbers)
    settings.WHATSAPP_ALLOWED_NUMBERS = allowed_numbers
    write_env_value("WHATSAPP_ALLOWED_NUMBERS", allowed_numbers)

    generated_secret = False
    if not settings.WHATSAPP_BRIDGE_SECRET:
        secret = secrets_module.token_urlsafe(32)
        settings.WHATSAPP_BRIDGE_SECRET = secret
        write_env_value("WHATSAPP_BRIDGE_SECRET", secret)
        # whatsapp-bridge/ est un process Node.js séparé (voir son README) : il DOIT avoir
        # exactement le même secret, dans SON propre .env, pas celui du backend.
        write_env_value("WHATSAPP_BRIDGE_SECRET", secret, env_path=WHATSAPP_BRIDGE_ENV_PATH)
        generated_secret = True

    was_enabled = _is_plugin_enabled("whatsapp")
    enable_result = set_plugin_enabled("whatsapp", True)

    # start_whatsapp_bridge() est un no-op s'il tourne déjà (voir lifecycle.py) : un changement de
    # numéros autorisés ne justifie jamais de le redémarrer (ça couperait une session WhatsApp déjà
    # liée, voir le docstring du module). Best-effort : ne peut pas lever d'exception.
    bridge_started = lifecycle.start_whatsapp_bridge()

    return {
        "status": "updated",
        "allowed_numbers": allowed_numbers,
        "secret_generated": generated_secret,
        "plugin_enabled": enable_result["enabled"],
        "plugin_newly_enabled": not was_enabled,
        # Seule la toute première activation nécessite un redémarrage du BACKEND (pour que FastAPI
        # monte /api/whatsapp/*, voir plugin_loader.py) — le pont, lui, vient d'être lancé ci-dessus
        # sans attendre ce redémarrage.
        "restart_required": not was_enabled,
        "bridge_auto_started": bridge_started,
    }


@router.post("/whatsapp-disconnect", dependencies=[Depends(require_api_key)])
async def disconnect_whatsapp():
    if not settings.WHATSAPP_BRIDGE_SECRET:
        raise HTTPException(status_code=503, detail="WhatsApp non configuré")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{settings.WHATSAPP_BRIDGE_URL.rstrip('/')}/logout",
                headers={"X-Bridge-Secret": settings.WHATSAPP_BRIDGE_SECRET},
            )
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"Impossible de déconnecter WhatsApp : {error}") from error
    return {
        "status": "disconnected",
        "detail": "WhatsApp est dissocié. Un nouveau QR code va être généré.",
    }


@router.get("/telegram-config", dependencies=[Depends(require_api_key)])
async def get_telegram_config():
    _reload_telegram_token_from_env()
    return {
        "allowed_user_ids": settings.TELEGRAM_ALLOWED_USER_IDS,
        "bot_token_configured": bool(settings.TELEGRAM_BOT_TOKEN),
        "secret_configured": bool(settings.TELEGRAM_BRIDGE_SECRET),
    }


@router.post("/telegram-users", dependencies=[Depends(require_api_key)])
async def discover_telegram_users(payload: TelegramDiscoveryRequest):
    _reload_telegram_token_from_env()
    bot_token = (payload.bot_token or settings.TELEGRAM_BOT_TOKEN).strip()
    if not bot_token:
        raise HTTPException(status_code=422, detail="Saisis d'abord le token du bot")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/getUpdates",
                json={"allowed_updates": ["message"]},
            )
            telegram_payload = response.json()
            if not response.is_success or not telegram_payload.get("ok"):
                detail = telegram_payload.get("description") or "Telegram a refusé le token"
                raise HTTPException(status_code=502, detail=detail)
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError) as error:
        logger.warning("[Messagerie] Détection des utilisateurs Telegram impossible : %s", error)
        raise HTTPException(
            status_code=502,
            detail="Telegram ne répond pas. Vérifie le token et réessaie.",
        ) from error

    users = {}
    for update in telegram_payload.get("result", []):
        message = update.get("message")
        sender = message.get("from") if isinstance(message, dict) else None
        chat = message.get("chat") if isinstance(message, dict) else None
        if not isinstance(sender, dict) or not isinstance(chat, dict) or chat.get("type") != "private":
            continue
        user_id = str(sender.get("id", "")).strip()
        if not user_id:
            continue
        users[user_id] = {
            "id": user_id,
            "first_name": str(sender.get("first_name", "")).strip(),
            "last_name": str(sender.get("last_name", "")).strip(),
            "username": str(sender.get("username", "")).strip(),
        }
    return {"users": list(users.values())}


@router.put("/telegram-config", dependencies=[Depends(require_api_key)])
async def update_telegram_config(payload: TelegramConfig):
    if not USER_ID_LIST_PATTERN.match(payload.allowed_user_ids):
        raise HTTPException(status_code=422, detail="Identifiants invalides : chiffres et virgules uniquement")

    allowed_ids = _normalize_list(payload.allowed_user_ids)
    if not allowed_ids:
        raise HTTPException(
            status_code=422,
            detail="Ajoute ton identifiant Telegram numérique pour autoriser ton compte",
        )
    settings.TELEGRAM_ALLOWED_USER_IDS = allowed_ids
    write_env_value("TELEGRAM_ALLOWED_USER_IDS", allowed_ids)

    bot_token = (payload.bot_token or "").strip()
    if bot_token:
        settings.TELEGRAM_BOT_TOKEN = bot_token
        write_env_value("TELEGRAM_BOT_TOKEN", bot_token)
    else:
        _reload_telegram_token_from_env()
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=422, detail="Token du bot manquant (créé via @BotFather sur Telegram)")

    if not settings.TELEGRAM_BRIDGE_SECRET:
        secret = secrets_module.token_urlsafe(32)
        settings.TELEGRAM_BRIDGE_SECRET = secret
        write_env_value("TELEGRAM_BRIDGE_SECRET", secret)
        # Pas de fichier séparé à synchroniser ici : telegram_bot.py charge le même backend/.env
        # (voir son docstring) — contrairement à whatsapp-bridge/, qui a le sien.

    was_enabled = _is_plugin_enabled("telegram")
    enable_result = set_plugin_enabled("telegram", True)

    # Contrairement à WhatsApp : un nouveau token DOIT redémarrer telegram_bot.py (le process ne le
    # relit jamais après son lancement, voir Application.builder().token(...) dans telegram_bot.py).
    # Sans changement de token, un simple start (no-op s'il tourne déjà) suffit — les identifiants
    # autorisés sont lus en direct par le backend, pas par ce process.
    if bot_token:
        bot_started = lifecycle.restart_telegram_bot()
    else:
        bot_started = lifecycle.start_telegram_bot()

    return {
        "status": "updated",
        "allowed_user_ids": allowed_ids,
        "bot_token_updated": bool(bot_token),
        "plugin_enabled": enable_result["enabled"],
        "plugin_newly_enabled": not was_enabled,
        "restart_required": not was_enabled,
        "bot_auto_started": bot_started,
        "bot_restarted": bool(bot_token),
    }


@router.post("/telegram-disconnect", dependencies=[Depends(require_api_key)])
async def disconnect_telegram():
    lifecycle.stop_telegram_bot()
    settings.TELEGRAM_BOT_TOKEN = ""
    settings.TELEGRAM_ALLOWED_USER_IDS = ""
    write_env_value("TELEGRAM_BOT_TOKEN", "")
    write_env_value("TELEGRAM_ALLOWED_USER_IDS", "")
    return {
        "status": "disconnected",
        "detail": "Telegram est déconnecté localement. Le bot Telegram n'a pas été supprimé.",
    }


# Carnet de contacts persistant dans la base SQLAlchemy principale (SQLite par défaut).
@router.get("/contacts", dependencies=[Depends(require_api_key)])
async def get_contacts():
    return {"contacts": await contacts_store.list_contacts()}


@router.put("/contacts", dependencies=[Depends(require_api_key)])
async def save_contact(payload: ContactPayload):
    whatsapp = payload.whatsapp.strip() if payload.whatsapp else None
    telegram = payload.telegram.strip() if payload.telegram else None
    if whatsapp and not NUMBER_LIST_PATTERN.match(whatsapp):
        raise HTTPException(status_code=422, detail="Numéro WhatsApp invalide : chiffres et \"+\" uniquement")
    if telegram and not USER_ID_LIST_PATTERN.match(telegram):
        raise HTTPException(status_code=422, detail="Identifiant Telegram invalide : chiffres uniquement")
    if not whatsapp and not telegram:
        raise HTTPException(status_code=422, detail="Renseigne au moins un numéro WhatsApp ou un identifiant Telegram")
    whatsapp_digits = _normalize_list(whatsapp) if whatsapp else None
    contact = await contacts_store.upsert_contact(payload.name, whatsapp_digits, telegram)
    return {"status": "saved", "contact": contact}


@router.delete("/contacts/{name}", dependencies=[Depends(require_api_key)])
async def remove_contact(name: str):
    if not await contacts_store.delete_contact(name):
        raise HTTPException(status_code=404, detail="Contact introuvable")
    return {"status": "deleted"}
