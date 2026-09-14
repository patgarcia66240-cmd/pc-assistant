"""Reconnexion automatique au téléphone Android au démarrage du backend, si un appairage a
déjà été enregistré (voir store.py) — même principe que plugins/messaging/lifecycle.py : du
best-effort qui ne doit jamais faire échouer le démarrage du backend (téléphone éteint, hors
du réseau Wi-Fi, IP qui a changé... tous des cas normaux, juste loggés)."""
import logging

from . import store
from .client import AndroidBridgeError, client

logger = logging.getLogger(__name__)


async def on_startup() -> None:
    config = store.load_config()
    if config is None:
        return
    try:
        await client.connect(config["host"], config["port"], config["token"])
        logger.info("[android_bridge] Reconnecté automatiquement à %s:%s", config["host"], config["port"])
    except AndroidBridgeError as error:
        logger.warning("[android_bridge] Reconnexion automatique impossible : %s", error)


async def on_shutdown() -> None:
    await client.disconnect()
