"""Intégration Google Agenda (OAuth2 + événements, lecture/écriture).

Appels API en httpx pur (pas de lib officielle google-auth/google-api-python-client) : cohérent
avec le reste du backend, qui fait déjà ses appels externes en httpx (météo/anniversaires dans
saint_service.py). Flux OAuth "Web application" (pas "Desktop app") : le client_secret reste
confidentiel côté serveur (dans .env), jamais exposé au frontend — voir les instructions de
configuration Google Cloud fournies séparément pour créer les identifiants.

Spécifications vérifiées le 10/09/2026 sur developers.google.com (OAuth 2.0 for Web Server
Applications + Google Calendar API v3 events reference) : endpoints, paramètres et scope exacts.
"""
import asyncio
import json
import secrets
import time
from pathlib import Path
from urllib.parse import quote, urlencode

import httpx

from config import settings

# Stocké à côté de .env (même niveau de confidentialité, même mécanisme .gitignore) — jamais dans
# backend/data/ qui contient des données de référence versionnées (saints_calendar.json...).
_TOKEN_PATH = Path(__file__).resolve().parent.parent / "google_calendar_token.json"

_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
# calendar.events (pas calendar tout court) : lecture/écriture des événements uniquement, pas la
# gestion des agendas eux-mêmes (création/suppression d'agendas, partage...) — principe du moindre
# privilège, on ne demande que ce dont ARIA a besoin.
# calendar.calendarlist.readonly (ajouté le 10/09/2026, vérifié sur developers.google.com) : lister
# les agendas visibles du compte (calendarList.list), nécessaire pour agréger les événements de
# TOUS les agendas de l'utilisatrice et pas seulement l'agenda principal — voir list_events. Un
# compte déjà connecté AVANT cet ajout n'a ce scope sur son refresh_token qu'après une reconnexion
# (disconnect() + reconnexion) ; en attendant, list_events se rabat sur l'agenda principal seul.
_SCOPE = (
    "https://www.googleapis.com/auth/calendar.events "
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly"
)

# État CSRF anti-forgery pour le callback OAuth. En mémoire process (appli locale
# mono-utilisateur, un seul flux de connexion à la fois) : généré par get_auth_url(), vérifié par
# exchange_code() avant tout échange de code contre un token.
_pending_state = None


class OAuthStateError(Exception):
    """Le paramètre state renvoyé par Google ne correspond pas à celui généré par get_auth_url()
    (ou aucune connexion n'était en cours) — callback rejeté par sécurité (anti-CSRF)."""


class CalendarNotConnectedError(Exception):
    """Aucun refresh_token stocké : l'utilisatrice n'a pas (encore) connecté son Google Agenda."""


def _load_tokens():
    if not _TOKEN_PATH.exists():
        return None
    try:
        return json.loads(_TOKEN_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_tokens(data: dict) -> None:
    _TOKEN_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_configured() -> bool:
    """Identifiants OAuth présents dans .env — préalable posé par l'utilisatrice elle-même
    (création du projet Google Cloud + identifiants), je ne peux pas le faire à sa place."""
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def is_connected() -> bool:
    tokens = _load_tokens()
    return bool(tokens and tokens.get("refresh_token"))


def get_auth_url() -> str:
    global _pending_state
    _pending_state = secrets.token_urlsafe(24)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_CALENDAR_REDIRECT_URI,
        "response_type": "code",
        "scope": _SCOPE,
        # offline + consent : garantit un refresh_token à CHAQUE connexion (Google ne le renvoie
        # sinon qu'à la toute première autorisation) — nécessaire pour se reconnecter après une
        # déconnexion volontaire (disconnect()) sans repasser par une réinitialisation manuelle
        # côté Google.
        "access_type": "offline",
        "prompt": "consent",
        "state": _pending_state,
    }
    return f"{_AUTH_ENDPOINT}?{urlencode(params)}"


async def exchange_code(code: str, state: str) -> None:
    global _pending_state
    if not _pending_state or state != _pending_state:
        raise OAuthStateError("state invalide ou expiré")
    _pending_state = None
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(_TOKEN_ENDPOINT, data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_CALENDAR_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        response.raise_for_status()
        data = response.json()
    # -60s de marge pour ne jamais utiliser un token expiré pile au moment de l'appel suivant.
    _save_tokens({
        "refresh_token": data["refresh_token"],
        "access_token": data.get("access_token"),
        "expires_at": time.time() + data.get("expires_in", 0) - 60,
    })


async def _refresh_access_token(tokens: dict) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(_TOKEN_ENDPOINT, data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": tokens["refresh_token"],
            "grant_type": "refresh_token",
        })
        response.raise_for_status()
        data = response.json()
    tokens["access_token"] = data["access_token"]
    tokens["expires_at"] = time.time() + data.get("expires_in", 0) - 60
    _save_tokens(tokens)
    return tokens


async def _get_valid_access_token():
    tokens = _load_tokens()
    if not tokens or not tokens.get("refresh_token"):
        return None
    if not tokens.get("access_token") or time.time() >= tokens.get("expires_at", 0):
        tokens = await _refresh_access_token(tokens)
    return tokens["access_token"]


def disconnect() -> None:
    if _TOKEN_PATH.exists():
        _TOKEN_PATH.unlink()


async def _authed_request(method: str, path: str, **kwargs):
    access_token = await _get_valid_access_token()
    if not access_token:
        raise CalendarNotConnectedError("Google Agenda non connecté")
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {access_token}"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.request(method, f"{_CALENDAR_API_BASE}{path}", headers=headers, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else None


async def list_calendars() -> list:
    """Agendas visibles du compte connecté (calendarList.list — nécessite le scope
    calendar.calendarlist.readonly, voir _SCOPE). "Visibles" = cochés dans Google Agenda
    (selected=true) ou l'agenda principal lui-même (primary=true, pas toujours marqué selected) :
    même ensemble que ce que l'utilisatrice voit affiché dans son Google Agenda."""
    data = await _authed_request("GET", "/users/me/calendarList", params={"minAccessRole": "reader"})
    items = data.get("items", []) if data else []
    return [c for c in items if c.get("selected") or c.get("primary")]


async def list_events(time_min: str, time_max: str) -> list:
    """time_min/time_max : datetimes RFC3339 avec offset (ex. 2026-09-01T00:00:00+02:00).
    Agrège les événements de TOUS les agendas visibles du compte (pas seulement l'agenda
    principal) : une utilisatrice a souvent plusieurs agendas Google (partagés, abonnements...) et
    Google Agenda les affiche tous ensemble — se limiter à "primary" faisait manquer des
    événements réels. Chaque événement renvoyé porte un champ calendarId ajouté ici (absent de la
    réponse brute de l'API), pour que update_event/delete_event ciblent le bon agenda ensuite."""
    try:
        calendars = await list_calendars()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 403:
            raise
        # Scope calendar.calendarlist.readonly pas encore accordé sur ce refresh_token (compte
        # connecté avant son ajout, reconnexion pas encore faite) : repli sur l'agenda principal
        # seul plutôt que de casser toute la fonctionnalité en attendant.
        calendars = []
    if not calendars:
        calendars = [{"id": "primary"}]

    async def _fetch(calendar_id: str) -> list:
        data = await _authed_request("GET", f"/calendars/{quote(calendar_id, safe='')}/events", params={
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": "true",  # développe les événements récurrents en occurrences uniques
            "orderBy": "startTime",
            "maxResults": 2500,
        })
        items = data.get("items", []) if data else []
        for item in items:
            item["calendarId"] = calendar_id
        return items

    results = await asyncio.gather(*(_fetch(calendar["id"]) for calendar in calendars))
    events = [event for calendar_events in results for event in calendar_events]
    events.sort(key=lambda e: e.get("start", {}).get("dateTime") or e.get("start", {}).get("date") or "")
    return events


async def create_event(payload: dict) -> dict:
    return await _authed_request("POST", "/calendars/primary/events", json=payload)


async def update_event(event_id: str, payload: dict, calendar_id: str = "primary") -> dict:
    return await _authed_request(
        "PATCH", f"/calendars/{quote(calendar_id, safe='')}/events/{event_id}", json=payload
    )


async def delete_event(event_id: str, calendar_id: str = "primary") -> None:
    await _authed_request("DELETE", f"/calendars/{quote(calendar_id, safe='')}/events/{event_id}")
