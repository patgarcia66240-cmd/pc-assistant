"""Routes Google Agenda : connexion OAuth + événements (lecture/écriture réelles, aucune donnée
fictive — tant que rien n'est connecté, ces routes renvoient un état "non connecté" plutôt que
d'inventer des événements)."""
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from config import settings
from services import google_calendar_service as gcal
from security import require_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


class EventPayload(BaseModel):
    summary: str
    description: Optional[str] = None
    location: Optional[str] = None
    start: dict
    end: dict


def _calendar_error(exc: Exception) -> HTTPException:
    if isinstance(exc, gcal.CalendarNotConnectedError):
        return HTTPException(409, "Google Agenda non connecté")
    if isinstance(exc, httpx.HTTPStatusError):
        logger.error(
            "Erreur Google Agenda (%s): %s",
            exc.response.status_code,
            exc.response.text,
        )
        return HTTPException(exc.response.status_code, "Erreur Google Agenda")
    logger.exception("Erreur inattendue Google Agenda", exc_info=exc)
    return HTTPException(502, "Service Google Agenda indisponible")


@router.get("/status")
async def calendar_status():
    return {
        "configured": gcal.is_configured(),
        "connected": gcal.is_connected(),
    }


@router.get("/auth-url", dependencies=[Depends(require_api_key)])
async def calendar_auth_url():
    if not gcal.is_configured():
        raise HTTPException(400, "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET manquants dans backend/.env")
    return {"url": gcal.get_auth_url()}


@router.get("/oauth/callback")
async def calendar_oauth_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    """Point de retour appelé par Google (redirect_uri), jamais par le frontend directement.
    Redirige ensuite vers l'appli (CORS_ORIGINS) avec un paramètre indiquant le résultat, que le
    composant Agenda lit au chargement pour afficher le statut et nettoyer l'URL."""
    frontend = settings.CORS_ORIGINS.split(",")[0].strip()
    if error:
        return RedirectResponse(f"{frontend}/?calendar_error={error}")
    if not code or not state:
        return RedirectResponse(f"{frontend}/?calendar_error=reponse_google_incomplete")
    try:
        await gcal.exchange_code(code, state)
    except gcal.OAuthStateError:
        return RedirectResponse(f"{frontend}/?calendar_error=state_invalide")
    except httpx.HTTPStatusError as exc:
        # Log complet côté serveur (visible dans le terminal où tourne uvicorn) : le paramètre
        # d'erreur renvoyé au frontend reste générique (jamais de detail Google dans l'URL), mais
        # sans ce log le vrai motif (client_secret invalide, code déjà utilisé...) était invisible.
        logger.error("Échange de code OAuth Google Agenda échoué (%s) : %s", exc.response.status_code, exc.response.text)
        return RedirectResponse(f"{frontend}/?calendar_error=echange_token_echoue")
    return RedirectResponse(f"{frontend}/?calendar_connected=1")


@router.post("/disconnect", dependencies=[Depends(require_api_key)])
async def calendar_disconnect():
    gcal.disconnect()
    return {"status": "disconnected"}


@router.get("/events", dependencies=[Depends(require_api_key)])
async def calendar_events(time_min: str = Query(...), time_max: str = Query(...)):
    try:
        items = await gcal.list_events(time_min, time_max)
    except (gcal.CalendarNotConnectedError, httpx.HTTPStatusError) as exc:
        raise _calendar_error(exc)
    return {"events": items}


@router.post("/events", dependencies=[Depends(require_api_key)])
async def calendar_create_event(payload: EventPayload):
    try:
        return await gcal.create_event(payload.model_dump(exclude_none=True))
    except (gcal.CalendarNotConnectedError, httpx.HTTPStatusError) as exc:
        raise _calendar_error(exc)


@router.patch("/events/{event_id}", dependencies=[Depends(require_api_key)])
async def calendar_update_event(event_id: str, payload: EventPayload, calendar_id: str = Query("primary")):
    try:
        return await gcal.update_event(event_id, payload.model_dump(exclude_none=True), calendar_id)
    except (gcal.CalendarNotConnectedError, httpx.HTTPStatusError) as exc:
        raise _calendar_error(exc)


@router.delete("/events/{event_id}", dependencies=[Depends(require_api_key)])
async def calendar_delete_event(event_id: str, calendar_id: str = Query("primary")):
    try:
        await gcal.delete_event(event_id, calendar_id)
    except (gcal.CalendarNotConnectedError, httpx.HTTPStatusError) as exc:
        raise _calendar_error(exc)
    return {"status": "deleted"}
