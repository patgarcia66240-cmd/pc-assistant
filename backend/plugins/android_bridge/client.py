"""Client WebSocket vers l'app compagnon ARIA Phone Bridge (Kotlin, voir android/).

Protocole (JSON, un message par frame texte) :
  PC -> téléphone :
    {"type": "auth", "token": "<jeton d'appairage>"}
    {"type": "request", "id": "<uuid4>", "action": "get_capabilities" | "get_device_info" | "get_contacts"}
  Téléphone -> PC :
    {"type": "auth_result", "ok": true, "device": {...}} ou {"ok": false, "error": "..."}
    {"type": "response", "id": "<uuid4>", "ok": true, "data": ...} ou {"ok": false, "error": "..."}

Une seule connexion à la fois (un PC, un téléphone) : c'est l'usage attendu (appairage
personnel), pas un serveur multi-clients. Les requêtes concurrentes sont mises en
correspondance par leur "id" (uuid4) via des asyncio.Future, comme un client JSON-RPC
classique — plusieurs GET /api/android/* peuvent donc être en vol en même temps sur la même
connexion sans se marcher dessus.
"""
import asyncio
import json
import logging
import uuid
from typing import Any, Optional

import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)

AUTH_TIMEOUT_SECONDS = 8
REQUEST_TIMEOUT_SECONDS = 15


class AndroidBridgeError(Exception):
    """Erreur métier renvoyée par le téléphone (ou par l'échec de connexion), déjà en
    français : router.py peut la renvoyer telle quelle au frontend."""


class AndroidGatewayClient:
    def __init__(self) -> None:
        self._connection: Optional[websockets.WebSocketClientProtocol] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._pending: dict[str, asyncio.Future] = {}
        self._device_info: Optional[dict] = None
        self._host: Optional[str] = None
        self._port: Optional[int] = None

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and not self._connection.closed

    @property
    def device_info(self) -> Optional[dict]:
        return self._device_info

    @property
    def endpoint(self) -> Optional[dict]:
        if self._host is None:
            return None
        return {"host": self._host, "port": self._port}

    async def connect(self, host: str, port: int, token: str) -> dict:
        """Ouvre la connexion, s'authentifie, démarre la boucle de lecture. Lève
        AndroidBridgeError (message déjà en français) si l'appairage échoue à n'importe quelle
        étape — appelant (router.py ou lifecycle.py) décide comment réagir."""
        await self.disconnect()
        uri = f"ws://{host}:{port}/ws"
        try:
            connection = await asyncio.wait_for(websockets.connect(uri), timeout=AUTH_TIMEOUT_SECONDS)
        except (OSError, asyncio.TimeoutError) as error:
            raise AndroidBridgeError(
                f"Impossible de joindre le téléphone à {host}:{port} — vérifiez qu'il est sur le même "
                f"réseau Wi-Fi et que la passerelle est démarrée dans l'app ({error})."
            ) from error

        try:
            await connection.send(json.dumps({"type": "auth", "token": token}))
            raw = await asyncio.wait_for(connection.recv(), timeout=AUTH_TIMEOUT_SECONDS)
        except (ConnectionClosed, asyncio.TimeoutError) as error:
            await connection.close()
            raise AndroidBridgeError("Le téléphone n'a pas répondu à l'appairage (jeton incorrect ?).") from error

        message = json.loads(raw)
        if message.get("type") != "auth_result" or not message.get("ok"):
            await connection.close()
            raise AndroidBridgeError(message.get("error") or "Jeton d'appairage refusé par le téléphone.")

        self._connection = connection
        self._device_info = message.get("device")
        self._host, self._port = host, port
        self._reader_task = asyncio.create_task(self._read_loop())
        logger.info("[android_bridge] Connecté à %s:%s", host, port)
        return self._device_info or {}

    async def disconnect(self) -> None:
        if self._reader_task is not None:
            self._reader_task.cancel()
            self._reader_task = None
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
        for future in self._pending.values():
            if not future.done():
                future.set_exception(AndroidBridgeError("Connexion au téléphone interrompue."))
        self._pending.clear()
        self._device_info = None

    async def request(self, action: str) -> Any:
        if not self.is_connected or self._connection is None:
            raise AndroidBridgeError("Le téléphone n'est pas connecté. Appairez-le depuis l'onglet Téléphone.")

        request_id = uuid.uuid4().hex
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future
        try:
            await self._connection.send(json.dumps({"type": "request", "id": request_id, "action": action}))
            return await asyncio.wait_for(future, timeout=REQUEST_TIMEOUT_SECONDS)
        except asyncio.TimeoutError as error:
            raise AndroidBridgeError("Le téléphone n'a pas répondu à temps.") from error
        finally:
            self._pending.pop(request_id, None)

    async def _read_loop(self) -> None:
        """Tourne tant que la connexion est ouverte : distribue chaque "response" reçue au
        Future en attente correspondant (par "id"). Une fermeture de connexion (volontaire ou
        non) fait échouer toutes les requêtes encore en vol plutôt que de les laisser bloquées
        indéfiniment."""
        assert self._connection is not None
        try:
            async for raw in self._connection:
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if message.get("type") != "response":
                    continue
                future = self._pending.get(message.get("id"))
                if future is None or future.done():
                    continue
                if message.get("ok"):
                    future.set_result(message.get("data"))
                else:
                    future.set_exception(AndroidBridgeError(message.get("error") or "Erreur inconnue côté téléphone."))
        except ConnectionClosed:
            pass
        finally:
            logger.info("[android_bridge] Connexion au téléphone fermée")
            self._connection = None
            self._device_info = None
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(AndroidBridgeError("Connexion au téléphone interrompue."))
            self._pending.clear()


# Instance partagée : un seul appairage à la fois (voir docstring du module), utilisée à la
# fois par router.py (requêtes HTTP) et lifecycle.py (reconnexion automatique au démarrage).
client = AndroidGatewayClient()
