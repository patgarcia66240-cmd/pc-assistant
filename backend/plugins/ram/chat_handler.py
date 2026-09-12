"""Handler de chat pour la RAM disponible — extrait de routes/chat.py le 12/09/2026, comme
ram/city_info/heure_meteo/bourse/calendar (agenda IA) : dernier chantier de migration en plugins,
chat.py ne fait plus que router vers ces plugins puis vers Claude en dernier recours.
order=10 : c'était le tout premier bloc vérifié dans routes/chat.py, avant même les infos ville."""
from services.local_service import get_ram_answer, is_ram_request

matches = is_ram_request


async def handle(message: str, context: dict) -> dict:
    return {
        "response": get_ram_answer(),
        "source": "local",
        "source_type": "system",
    }
