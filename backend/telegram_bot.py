"""Pont Telegram pour ARIA — script séparé de main.py (comme whatsapp-bridge/ pour WhatsApp, mais
plus simple : API Telegram officielle et gratuite, pas de session à scanner ni de service à
exposer). Se lance dans le même environnement virtuel que le backend :

    cd backend
    python telegram_bot.py

Écoute les messages Telegram par "long polling" (c'est ce script qui va chercher les nouveaux
messages, pas l'inverse) : aucune exposition réseau nécessaire, contrairement à une intégration
WhatsApp officielle par webhook.

Pour chaque message reçu, appelle POST /api/telegram/incoming sur le backend ARIA (qui doit
tourner en même temps, python main.py) et répond directement avec le texte renvoyé — voir
backend/plugins/telegram/router.py pour le traitement (heure/météo, bourse, rois de France,
agenda IA, Claude en dernier recours, liste blanche d'utilisateurs autorisés).

Préparation (une fois) :
  1. Sur Telegram, écrire à @BotFather, envoyer /newbot et suivre les instructions -> il donne un
     token (garder secret, équivalent d'un mot de passe).
  2. Mettre ce token dans TELEGRAM_BOT_TOKEN (backend/.env).
  3. Mettre TELEGRAM_BRIDGE_SECRET (backend/.env) — n'importe quelle valeur aléatoire, ex :
     python -c "import secrets; print(secrets.token_urlsafe(32))"
  4. Écrire à @userinfobot sur Telegram pour connaître son propre identifiant numérique, l'ajouter
     à TELEGRAM_ALLOWED_USER_IDS (backend/.env) — sinon ARIA ignore tous les messages.
  5. Activer le plugin "telegram" dans l'onglet Plugins de l'app, redémarrer le backend.

Tant que ce script tourne, il écrit un heartbeat (backend/data/telegram_status.json) lu par
GET /api/telegram/status — c'est ce qui alimente l'onglet Messagerie du frontend (voir
backend/plugins/messaging/, ajouté le 12/09/2026).
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from config import settings

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
# Comme dans l'exemple officiel python-telegram-bot : sinon chaque requête HTTP interne de httpx
# (vers l'API Telegram ET vers le backend ARIA) pollue les logs au niveau INFO.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Heartbeat pour l'onglet Messagerie (frontend) : ce script tourne dans son propre process,
# séparé de main.py (voir backend/plugins/telegram/router.py), donc le backend ne peut pas
# savoir directement s'il est en vie. Solution la plus simple sans nouvelle dépendance
# (pas de job-queue PTB, pas de serveur HTTP local comme whatsapp-bridge/) : ce script écrit
# lui-même un petit fichier JSON avec l'heure de son dernier passage, et GET /api/telegram/status
# le lit en considérant "en ligne" si l'écriture date de moins de HEARTBEAT_STALE_AFTER secondes
# (voir la même constante côté router.py).
STATUS_PATH = Path(__file__).resolve().parent / "data" / "telegram_status.json"
HEARTBEAT_INTERVAL_SECONDS = 30


def _write_heartbeat(bot_username: str | None) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"last_seen": datetime.now(timezone.utc).isoformat(), "bot_username": bot_username}
    try:
        STATUS_PATH.write_text(json.dumps(payload), encoding="utf-8")
    except OSError as error:
        logger.warning("[ARIA][Telegram] Impossible d'écrire le heartbeat (%s) : %s", STATUS_PATH, error)


async def _heartbeat_loop(application: Application) -> None:
    while True:
        _write_heartbeat(application.bot.username)
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)


async def _on_startup(application: Application) -> None:
    # Écriture immédiate (pas d'attente du premier intervalle) : l'onglet Messagerie doit voir
    # le bot "en ligne" dès qu'il démarre, pas jusqu'à 30s plus tard. application.create_task lie
    # la tâche au cycle de vie de l'Application (arrêtée proprement avec le bot, contrairement à
    # un simple asyncio.create_task lancé à la main).
    application.create_task(_heartbeat_loop(application))


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return  # médias, stickers, etc. — non gérés pour l'instant

    user_id = str(update.effective_user.id)
    # first_name/last_name/username transmis en plus du texte — ajouté le 12/09/2026 pour que le
    # backend puisse construire un carnet des personnes ayant déjà écrit au bot (voir
    # plugins/telegram/router.py, _remember_user) : contrairement à WhatsApp/Baileys, l'API Bot
    # Telegram ne donne accès à aucun répertoire, seulement aux infos des gens qui écrivent.
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"http://{settings.API_HOST}:{settings.API_PORT}/api/telegram/incoming",
                json={
                    "user_id": user_id,
                    "message": update.message.text,
                    "first_name": update.effective_user.first_name,
                    "last_name": update.effective_user.last_name,
                    "username": update.effective_user.username,
                },
                headers={"X-Bridge-Secret": settings.TELEGRAM_BRIDGE_SECRET},
            )
            response.raise_for_status()
        reply_text = response.json().get("response") or "…"
    except httpx.HTTPError as error:
        logger.error("[ARIA][Telegram] Échec de l'appel au backend pour %s : %s", user_id, error)
        reply_text = "Désolée, je n'ai pas pu traiter ce message pour le moment (le backend ARIA tourne-t-il ?)."

    await update.message.reply_text(reply_text)


def main() -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN manquant dans backend/.env — voir l'en-tête de ce fichier.")
    if not settings.TELEGRAM_BRIDGE_SECRET:
        raise SystemExit("TELEGRAM_BRIDGE_SECRET manquant dans backend/.env — voir l'en-tête de ce fichier.")

    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).post_init(_on_startup).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    logger.info("[ARIA][Telegram] Bot démarré, en écoute (Ctrl+C pour arrêter)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
