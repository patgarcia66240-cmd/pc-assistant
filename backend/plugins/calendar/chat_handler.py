"""Assistant agenda IA dans le chat — extrait de routes/chat.py le 12/09/2026 (dernier bloc du
chantier de migration, voir aussi ram/city_info/heure_meteo/bourse). Cohabite avec router.py
(OAuth + événements REST, onglet Agenda) dans le même plugin "calendar" : les deux facettes
parlent du même Google Agenda connecté — pas de raison d'en faire un plugin séparé.

order=200 (bien après kings=100/quiz=90) : dans routes/chat.py, ce bloc arrivait après la boucle
sur les plugin chat handlers existants (donc après eux), juste avant le repli final sur Claude
seul — un ordre élevé reproduit exactement cette position."""
from fastapi import HTTPException

from config import settings
from services import calendar_assistant
from services import google_calendar_service as gcal
from services.claude_service import claude_service

matches = calendar_assistant.is_calendar_request


async def handle(message: str, context: dict) -> dict:
    if not gcal.is_configured() or not gcal.is_connected():
        return {
            "response": "Ton Google Agenda n'est pas encore connecté. Va dans l'onglet Agenda pour le connecter, puis redemande-moi.",
            "source": "local",
            "source_type": "calendar_not_connected",
        }
    if claude_service.client is None:
        raise HTTPException(status_code=503, detail="Claude API is not configured")
    # SERVICE_ERRORS (httpx.HTTPError, LookupError, IndexError, KeyError, ValueError, TypeError)
    # levée par calendar_assistant.run() remonte telle quelle : le mécanisme générique de
    # plugin_loader la convertit en 502 avec le chat_error_message du manifest ("Assistant agenda
    # indisponible", identique au message d'origine dans chat.py) — pas besoin de la rattraper ici,
    # contrairement à bourse/heure_meteo où plusieurs messages distincts devaient être préservés.
    response = await calendar_assistant.run(message, claude_service.client, settings.CLAUDE_MODEL)
    return {
        "response": response,
        "source": "ai",
        "source_type": "calendar_assistant",
    }
