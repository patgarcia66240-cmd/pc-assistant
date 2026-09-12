"""Lance et arrête automatiquement les process externes de messagerie (whatsapp-bridge/,
telegram_bot.py) avec le backend — ajouté le 12/09/2026 à la demande de Sarah : avant, il
fallait ouvrir un terminal séparé et taper "npm start" / "python telegram_bot.py" à chaque
démarrage d'ARIA.

Deux points d'entrée :
  - on_startup()/on_shutdown() : appelés automatiquement via le mécanisme générique de
    plugin_loader.get_lifecycle_hooks() (voir manifest.json, "lifecycle": true), une fois au
    démarrage du backend et une fois à l'arrêt (voir main.py, lifespan).
  - start_whatsapp_bridge()/start_telegram_bot() : appelées aussi directement par router.py
    juste après un "Enregistrer et activer" réussi dans l'onglet Messagerie, pour ne pas
    attendre le prochain redémarrage du backend avant que le pont tourne déjà.

Tout ici est du best-effort volontaire : un échec de lancement (déjà lancé, pas configuré,
"npm install" jamais fait, "node" absent du PATH...) est juste loggé, jamais une exception qui
remonterait et casserait le démarrage du backend ou la sauvegarde d'un formulaire. Les logs de
chaque process vont dans run-logs/ à la racine du repo (pas DEVNULL, pas backend/data/logs/ — voir
pourquoi juste en dessous, LOG_DIR) : utile pour diagnostiquer si un pont ne démarre pas, puisqu'il
n'y a plus de terminal visible pour les lire en direct.

Limite connue : subprocess.Popen ne suit que SES PROPRES enfants. Si Sarah a déjà lancé
whatsapp-bridge/ à la main dans un terminal séparé, ce module ne le voit pas — une nouvelle
tentative de lancement échouera simplement (port 3001 déjà pris), sans arrêter celui déjà en
cours ni le remplacer. Pareil au shutdown : on_shutdown() n'arrête que ce que CE process a
lancé lui-même."""
import logging
import shutil
import subprocess
import sys
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)

# backend/plugins/messaging/lifecycle.py -> .parent=messaging, .parent.parent=plugins,
# .parent.parent.parent=backend, .parent.parent.parent.parent=racine du repo (contient
# whatsapp-bridge/, en frère de backend/).
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BACKEND_DIR.parent
WHATSAPP_BRIDGE_DIR = REPO_ROOT / "whatsapp-bridge"
# ATTENTION : ces logs doivent rester EN DEHORS de backend/ — bug trouvé le 12/09/2026 : main.py
# lance uvicorn avec reload=True et reload_dirs=[backend/] (voir son docstring), qui surveille
# TOUS les fichiers de ce dossier, pas seulement les .py. Si ces logs étaient dans
# backend/data/logs/ (comme au tout premier essai), chaque écriture (ex. whatsapp-bridge/ qui
# plante et loggue son erreur) redémarre le backend, qui relance whatsapp-bridge/ via on_startup,
# qui replante, qui réécrit le log, qui redémarre le backend... une boucle infinie qui rendait le
# backend injoignable en continu (HTTP 502 côté frontend). D'où run-logs/ à la racine du repo,
# jamais dans backend/.
LOG_DIR = REPO_ROOT / "run-logs"

_whatsapp_process: subprocess.Popen | None = None
_telegram_process: subprocess.Popen | None = None
# Handles de fichiers de logs gardés ouverts tant que le process tourne (fermés par l'OS à la
# fin du process de toute façon, mais autant les référencer pour éviter tout garbage-collection
# prématuré du descripteur de fichier pendant que le sous-process écrit dedans).
_log_handles: list = []


def _is_running(process: subprocess.Popen | None) -> bool:
    return process is not None and process.poll() is None


def _stop(process: subprocess.Popen | None, name: str) -> None:
    if not _is_running(process):
        return
    logger.info("[Messagerie] Arrêt de %s (pid %s)...", name, process.pid)
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def _open_log(name: str):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handle = open(LOG_DIR / f"{name}.log", "a", encoding="utf-8")
    _log_handles.append(handle)
    return handle


def start_whatsapp_bridge() -> bool:
    """Lance whatsapp-bridge/ (node index.js). Renvoie True si un lancement a été tenté (pas
    forcément réussi — voir le docstring du module pour les cas non bloquants)."""
    global _whatsapp_process
    if _is_running(_whatsapp_process):
        return False
    if not settings.WHATSAPP_BRIDGE_SECRET:
        return False
    if not (WHATSAPP_BRIDGE_DIR / "node_modules").exists():
        logger.warning('[Messagerie] whatsapp-bridge/node_modules absent — lance "npm install" une première fois dans whatsapp-bridge/.')
        return False
    node = shutil.which("node")
    if not node:
        logger.warning('[Messagerie] "node" introuvable dans le PATH — impossible de lancer whatsapp-bridge/ automatiquement.')
        return False
    try:
        log_file = _open_log("whatsapp-bridge")
        _whatsapp_process = subprocess.Popen(
            [node, "index.js"],
            cwd=str(WHATSAPP_BRIDGE_DIR),
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    except OSError as error:
        logger.warning("[Messagerie] Échec du lancement de whatsapp-bridge/ : %s", error)
        return False
    logger.info("[Messagerie] whatsapp-bridge/ lancé (pid %s) — logs dans %s", _whatsapp_process.pid, LOG_DIR / "whatsapp-bridge.log")
    return True


def start_telegram_bot() -> bool:
    """Lance backend/telegram_bot.py avec le même interpréteur Python que ce backend
    (sys.executable, donc le même venv — pas besoin de le réactiver)."""
    global _telegram_process
    if _is_running(_telegram_process):
        return False
    if not (settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BRIDGE_SECRET):
        return False
    try:
        log_file = _open_log("telegram_bot")
        _telegram_process = subprocess.Popen(
            [sys.executable, "telegram_bot.py"],
            cwd=str(BACKEND_DIR),
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    except OSError as error:
        logger.warning("[Messagerie] Échec du lancement de telegram_bot.py : %s", error)
        return False
    logger.info("[Messagerie] telegram_bot.py lancé (pid %s) — logs dans %s", _telegram_process.pid, LOG_DIR / "telegram_bot.log")
    return True


def restart_whatsapp_bridge() -> bool:
    """Coupe puis relance whatsapp-bridge/ — PAS utilisée par router.py (voir son docstring,
    corrigé le 12/09/2026) : un redémarrage couperait une session WhatsApp déjà liée et forcerait
    un nouveau scan de QR code, alors que rien dans la config d'un pont déjà lancé n'en a jamais
    besoin (allowed_numbers est lu côté backend, pas par ce process ; le secret n'est écrit
    qu'une fois, avant le tout premier lancement — voir start_whatsapp_bridge). Gardée comme
    utilitaire au cas où un futur bouton "forcer une reconnexion" en aurait besoin."""
    global _whatsapp_process
    _stop(_whatsapp_process, "whatsapp-bridge")
    _whatsapp_process = None
    return start_whatsapp_bridge()


def stop_whatsapp_bridge() -> bool:
    global _whatsapp_process
    if not _is_running(_whatsapp_process):
        return False
    _stop(_whatsapp_process, "whatsapp-bridge")
    _whatsapp_process = None
    return True


def restart_telegram_bot() -> bool:
    """Coupe puis relance telegram_bot.py — utilisée par router.py UNIQUEMENT quand le token du
    bot vient de changer (le process ne le relit jamais après son lancement, voir
    Application.builder().token(...) dans telegram_bot.py) ; un simple changement d'identifiants
    autorisés utilise start_telegram_bot() à la place (no-op s'il tourne déjà)."""
    global _telegram_process
    _stop(_telegram_process, "telegram_bot.py")
    _telegram_process = None
    return start_telegram_bot()


def stop_telegram_bot() -> bool:
    global _telegram_process
    if not _is_running(_telegram_process):
        return False
    _stop(_telegram_process, "telegram_bot.py")
    _telegram_process = None
    return True


async def on_startup() -> None:
    """Appelé une fois au démarrage du backend (voir plugin_loader.get_lifecycle_hooks() et
    main.py) : lance chaque pont dont le plugin correspondant est déjà activé. Import de
    plugin_loader fait ICI (pas en haut du fichier) : plugin_loader importe ce module pour
    récupérer on_startup/on_shutdown, un import circulaire au niveau module serait sinon
    possible selon l'ordre de chargement."""
    from plugin_loader import list_plugin_status
    enabled = {plugin["id"]: plugin["enabled"] for plugin in list_plugin_status()}
    if enabled.get("whatsapp"):
        start_whatsapp_bridge()
    if enabled.get("telegram"):
        start_telegram_bot()


async def on_shutdown() -> None:
    """Termine proprement les process lancés PAR CE PROCESS à l'arrêt du backend."""
    for name, process in (("whatsapp-bridge", _whatsapp_process), ("telegram_bot.py", _telegram_process)):
        if _is_running(process):
            logger.info("[Messagerie] Arrêt de %s (pid %s)...", name, process.pid)
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    for handle in _log_handles:
        try:
            handle.close()
        except OSError:
            pass
