"""Routes REST du plugin android_bridge — pilotent le client WebSocket vers le téléphone
(voir client.py) : appairage, statut, et lecture des données exposées par l'app Android
(android/, capacités contacts/infos appareil, voir GatewayServer.kt côté Kotlin)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import store
from .client import AndroidBridgeError, client

router = APIRouter()


class PairRequest(BaseModel):
    host: str = Field(min_length=1)
    port: int = Field(gt=0, le=65535)
    token: str = Field(min_length=1)


@router.get("/status")
async def get_status():
    return {
        "connected": client.is_connected,
        "endpoint": client.endpoint,
        "device": client.device_info,
    }


@router.post("/pair")
async def pair(payload: PairRequest):
    """Appairage initial (ou ré-appairage avec un nouveau jeton) : le jeton et l'IP:port
    affichés dans l'app Android (onglet Passerelle) sont à saisir ici. Persisté dans
    backend/data/android_bridge.json pour la reconnexion automatique au démarrage du backend
    (voir lifecycle.py)."""
    try:
        device = await client.connect(payload.host, payload.port, payload.token)
    except AndroidBridgeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    store.save_config(payload.host, payload.port, payload.token)
    return {"connected": True, "device": device}


@router.post("/disconnect")
async def disconnect():
    """Coupe la connexion en cours sans oublier l'appairage (contrairement à /forget) — utile
    avant d'éteindre le téléphone sans avoir à ressaisir le jeton ensuite."""
    await client.disconnect()
    return {"connected": False}


@router.post("/forget")
async def forget():
    """Coupe la connexion ET oublie l'appairage : un nouveau /pair sera nécessaire."""
    await client.disconnect()
    store.clear_config()
    return {"connected": False, "forgotten": True}


@router.get("/capabilities")
async def get_capabilities():
    try:
        return {"capabilities": await client.request("get_capabilities")}
    except AndroidBridgeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/device-info")
async def get_device_info():
    try:
        return await client.request("get_device_info")
    except AndroidBridgeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/contacts")
async def get_contacts():
    try:
        return {"contacts": await client.request("get_contacts")}
    except AndroidBridgeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
