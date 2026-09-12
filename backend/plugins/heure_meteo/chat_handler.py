"""Handler de chat pour l'heure (locale, ville précisée, ou capitales du G7) et la météo —
extrait de routes/chat.py le 12/09/2026 (voir ram/city_info/bourse/calendar pour le reste du même
chantier). Trois cas regroupés dans l'ordre d'origine : capitales du G7 d'abord (déclencheur
distinct, "heure monde"/"heure g7"), puis heure, puis météo.

Erreurs : chaque cas gardait un message distinct dans chat.py ("Time service unavailable" vs
"Weather service unavailable") — préservé ici en les attrapant explicitement dans handle() plutôt
que de laisser le mécanisme générique de plugin_loader appliquer un seul chat_error_message aux
deux (voir manifest.json, "Time/weather service unavailable" n'est qu'un filet de secours au cas
où une erreur inattendue passerait au travers)."""
import re

import httpx
from fastapi import HTTPException

from services.local_service import (
    get_g7_time_answer,
    get_time_answer,
    get_weather_answer,
    is_time_request,
    is_weather_request,
    is_world_time_request,
)


def matches(message: str) -> bool:
    return is_world_time_request(message) or is_time_request(message) or is_weather_request(message)


def parse_time_response(response: str) -> dict:
    match = re.search(
        r"^Heure(?: en France| à (?P<location>.+?))? : (?P<time>\d{2}:\d{2}), le (?P<date>.+?) "
        r"\((?P<offset>UTC[+-]\d+), (?P<season>heure d'été|heure d'hiver)\)\. "
        r"Éphémérides : lever du soleil à (?P<sunrise>\d{2}:\d{2}), coucher du soleil à (?P<sunset>\d{2}:\d{2})\.?$",
        response,
    )
    if not match:
        return {}
    data = match.groupdict()
    data["location"] = data["location"] or "France"
    return data


async def handle(message: str, context: dict) -> dict:
    if is_world_time_request(message):
        return {
            "response": "Heure des capitales du G7",
            "data": get_g7_time_answer(),
            "source": "local",
            "source_type": "world_time",
        }

    if is_time_request(message):
        try:
            response = await get_time_answer(message, context.get("location"))
        except (httpx.HTTPError, IndexError, KeyError, ValueError, TypeError) as error:
            raise HTTPException(status_code=502, detail="Time service unavailable") from error
        time_data = parse_time_response(response)
        location_label = "Heure France"
        if response.startswith("Heure à "):
            location_name = response.removeprefix("Heure à ").split(" :", 1)[0]
            country_name = location_name.rsplit(",", 1)[-1].strip() if "," in location_name else location_name
            location_label = f"Heure {country_name}"
        return {
            "response": response,
            "time_data": time_data,
            "time_label": location_label,
            "source": "local",
            "source_type": "time",
        }

    # is_weather_request(message) — dernier cas possible, garanti par matches() ci-dessus.
    try:
        response = await get_weather_answer(message, context.get("location"))
    except (httpx.HTTPError, LookupError, IndexError, KeyError, ValueError, TypeError) as error:
        raise HTTPException(status_code=502, detail="Weather service unavailable") from error
    return {
        "response": response["text"],
        "source": "local",
        "source_type": "weather",
        "weather_type": response["weather_type"],
    }
