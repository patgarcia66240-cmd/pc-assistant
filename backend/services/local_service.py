"""Local system answers that do not require an AI provider."""
from datetime import datetime
import re
import unicodedata
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
import psutil

from config import settings

FRENCH_WEEKDAYS = (
    "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"
)
FRENCH_MONTHS = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    normalized = "".join(character for character in normalized if unicodedata.category(character) != "Mn")
    return normalized.replace("'", " ").replace("’", " ")


def format_gib(value: int) -> str:
    return f"{value / (1024 ** 3):.1f} Go"


def get_ram_answer() -> str:
    memory = psutil.virtual_memory()
    return f"RAM disponible : {format_gib(memory.available)} sur {format_gib(memory.total)}."


COUNTRY_NAMES = {
    "FR": "France",
    "US": "États-Unis",
    "CA": "Canada",
    "GB": "Royaume-Uni",
    "BE": "Belgique",
    "BG": "Bulgarie",
    "ES": "Espagne",
    "IT": "Italie",
    "DE": "Allemagne",
    "PT": "Portugal",
    "CH": "Suisse",
    "LU": "Luxembourg",
    "NL": "Pays-Bas",
    "IE": "Irlande",
    "AT": "Autriche",
    "GR": "Grèce",
    "SE": "Suède",
    "NO": "Norvège",
    "DK": "Danemark",
    "FI": "Finlande",
    "PL": "Pologne",
    "CZ": "Tchéquie",
    "RO": "Roumanie",
    "HU": "Hongrie",
    "TR": "Turquie",
    "MA": "Maroc",
    "DZ": "Algérie",
    "TN": "Tunisie",
    "SN": "Sénégal",
    "CI": "Côte d'Ivoire",
    "CM": "Cameroun",
    "ZA": "Afrique du Sud",
    "BR": "Brésil",
    "AR": "Argentine",
    "MX": "Mexique",
    "CL": "Chili",
    "CO": "Colombie",
    "AU": "Australie",
    "NZ": "Nouvelle-Zélande",
    "JP": "Japon",
    "CN": "Chine",
    "IN": "Inde",
    "KR": "Corée du Sud",
    "RU": "Russie",
}

COUNTRY_ALIASES = {normalize_text(name): code for code, name in COUNTRY_NAMES.items()}
COUNTRY_ALIASES.update({
    "angleterre": "GB",
    "grande bretagne": "GB",
    "royaume uni": "GB",
    "uk": "GB",
    "gb": "GB",
    "etats unis": "US",
    "usa": "US",
    "us": "US",
    "be": "BE",
    "bg": "BG",
    "espagne": "ES",
    "es": "ES",
    "allemagne": "DE",
    "de": "DE",
    "fr": "FR",
})


def country_code(value: str) -> str | None:
    normalized = normalize_text(value.strip()).replace("-", " ")
    if normalized in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[normalized]
    if len(normalized) == 2 and normalized.isalpha():
        return normalized.upper()
    return None


async def get_time_answer(message: str = "", location: dict | None = None) -> str:
    city = extract_city(message) if message else None
    if not city and message:
        normalized_message = normalize_text(message)
        city_match = re.search(r"\bheure\s+(?:de|a|pour)?\s*(.+)$", normalized_message)
        if city_match:
            candidate = city_match.group(1).strip(" ?.!	")
            comparison_candidate = candidate.replace("-", " ")
            if comparison_candidate not in {"actuelle", "est il", "du jour"} and not comparison_candidate.startswith("est il"):
                city = candidate
    # Ni ville précisée dans le message, ni position du navigateur transmise (context.location,
    # voir getBrowserLocation() dans VoiceAssistant.jsx — renvoie null si la géolocalisation est
    # refusée ou indisponible) : on utilise la localisation enregistrée dans Paramètres (Pays/Ville,
    # voir AppSettingsModal.jsx et backend/plugins/config/router.py) au lieu de renvoyer Paris/France
    # en dur. C'était le bug signalé : la réponse restait "Heure en France" (Paris) quelle que soit
    # la ville choisie dans les paramètres, dès que la géolocalisation navigateur n'était pas
    # disponible — ce qui est le cas la plupart du temps.
    using_saved_location = not city and not location
    timezone_name = "Europe/Paris"
    reference = settings.USER_CITY_LABEL if using_saved_location else "France"
    if location:
        latitude = location.get("latitude", settings.USER_LATITUDE)
        longitude = location.get("longitude", settings.USER_LONGITUDE)
    else:
        latitude = settings.USER_LATITUDE
        longitude = settings.USER_LONGITUDE

    async with httpx.AsyncClient(timeout=8) as client:
        if city:
            try:
                city_name, _, country = city.partition(",")
                code = country_code(country) if country else None
                geocoding_params = {
                    "name": geocoding_city_name(city_name.strip()),
                    "count": 1,
                    "language": "fr",
                    "format": "json",
                }
                if code:
                    geocoding_params["countryCode"] = code
                geocoding = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params=geocoding_params,
                )
                geocoding.raise_for_status()
                place = geocoding.json().get("results", [])[0]
                timezone_name = place.get("timezone") or timezone_name
                reference = f"{place.get('name', city.title())}, {COUNTRY_NAMES.get(place.get('country_code'), place.get('country', ''))}".strip(", ")
                latitude = place["latitude"]
                longitude = place["longitude"]
            except (httpx.HTTPError, KeyError, IndexError, TypeError):
                reference = city.title()
        elif location or using_saved_location:
            try:
                timezone_response = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={"latitude": latitude, "longitude": longitude, "current": "temperature_2m", "timezone": "auto"},
                )
                timezone_response.raise_for_status()
                timezone_name = timezone_response.json().get("timezone") or timezone_name
                # "votre position" seulement pour une vraie position GPS du navigateur — pour le
                # repli sur la localisation enregistrée, on garde le nom de ville (plus parlant).
                reference = "votre position" if location else settings.USER_CITY_LABEL
            except (httpx.HTTPError, KeyError, TypeError):
                pass

    # timezone_name peut venir d'une réponse API externe (open-meteo) : si jamais elle renvoie
    # une valeur vide/invalide, ZoneInfo() plante sans que ce soit une erreur réseau — on protège
    # ce point précis (c'était la cause d'un vrai crash 500 sur /api/chat/ pour les requêtes
    # d'heure avec une position/ville dont le fuseau horaire était mal renseigné).
    try:
        now = datetime.now(ZoneInfo(timezone_name))
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        timezone_name = "Europe/Paris"
        now = datetime.now(ZoneInfo(timezone_name))
    offset_hours = int(now.utcoffset().total_seconds() / 3600)
    offset = f"UTC{offset_hours:+d}"
    season = "heure d'été" if now.dst() else "heure d'hiver"
    french_date = (
        f"{FRENCH_WEEKDAYS[now.weekday()]} {now.day} "
        f"{FRENCH_MONTHS[now.month - 1]} {now.year}"
    )
    # `reference` est déjà correctement défini par les branches ci-dessus dans les trois cas
    # possibles (ville trouvée, position navigateur, ou repli sur la localisation enregistrée) —
    # `using_saved_location` couvre exactement le complément de `city or location`, donc il n'y a
    # plus de cas résiduel qui devrait retomber sur "France" ici (contrairement à avant, où ce repli
    # écrasait silencieusement le nom de ville enregistré).

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "daily": "sunrise,sunset",
                    "timezone": timezone_name,
                    "forecast_days": 1,
                },
            )
            response.raise_for_status()
            daily = response.json()["daily"]
            sunrise = datetime.fromisoformat(daily["sunrise"][0]).strftime("%H:%M")
            sunset = datetime.fromisoformat(daily["sunset"][0]).strftime("%H:%M")
            heading = "Heure en France" if reference == "France" else f"Heure à {reference}"
            return (
                f"{heading} : {now:%H:%M}, le {french_date} ({offset}, {season}). "
                f"Éphémérides : lever du soleil à {sunrise}, coucher du soleil à {sunset}."
            )
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        heading = "Heure en France" if reference == "France" else f"Heure à {reference}"
        return f"{heading} : {now:%H:%M}, le {french_date} ({offset}, {season})."


def get_g7_time_answer() -> str:
    capitals = (
        ("Washington", "America/New_York"),
        ("Ottawa", "America/Toronto"),
        ("Londres", "Europe/London"),
        ("Paris", "Europe/Paris"),
        ("Berlin", "Europe/Berlin"),
        ("Rome", "Europe/Rome"),
        ("Tokyo", "Asia/Tokyo"),
    )
    times = [
        {"city": capital, "time": f"{datetime.now(ZoneInfo(timezone_name)):%H:%M}"}
        for capital, timezone_name in capitals
    ]
    return times


def weather_description(code: int) -> str:
    descriptions = {
        0: "ciel dégagé",
        1: "globalement ensoleillé",
        2: "partiellement nuageux",
        3: "nuageux",
        45: "brumeux",
        48: "brouillard givrant",
        51: "bruine légère",
        53: "bruine",
        55: "bruine forte",
        56: "bruine verglaçante légère",
        57: "bruine verglaçante forte",
        61: "pluie légère",
        63: "pluie",
        65: "forte pluie",
        66: "pluie verglaçante légère",
        67: "forte pluie verglaçante",
        71: "neige légère",
        73: "neige",
        75: "fortes chutes de neige",
        77: "grains de neige",
        80: "averses légères",
        81: "averses",
        82: "fortes averses",
        85: "averses de neige légères",
        86: "fortes averses de neige",
        95: "orage",
        96: "orage avec grêle légère",
        99: "orage avec forte grêle",
    }
    return descriptions.get(code, "conditions variables")


def weather_icon_type(code: int) -> str:
    if code in (0, 1):
        return "clear"
    if code in (2, 3, 45, 48):
        return "cloud"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "storm"
    return "rain"


# Formules de politesse qu'on ne veut pas envoyer au géocodeur comme si c'était un nom de
# ville (ex. "météo s'il te plaît" -> extract_city renvoyait "s il te plait" sans ce filtre).
FILLER_SUFFIXES = (
    "s il te plait",
    "s il vous plait",
    "stp",
    "svp",
    "merci",
    "please",
)


def _strip_filler_suffix(city: str) -> str:
    # Plusieurs passes : "s'il te plaît stp" doit perdre les deux, pas juste la dernière trouvée.
    cleaned = city
    changed = True
    while changed:
        changed = False
        for filler in FILLER_SUFFIXES:
            new_cleaned = re.sub(rf"\s*,?\s*{re.escape(filler)}\s*$", "", cleaned).strip()
            if new_cleaned != cleaned:
                cleaned = new_cleaned
                changed = True
    return cleaned


def extract_city(message: str) -> str | None:
    normalized = normalize_text(message)
    match = re.search(r"\bmeteo\s+(.+)$", normalized)
    if match:
        city = match.group(1).strip(" ?.!	")
        city = re.sub(r"^(?:de|a|pour)\s+", "", city).strip()
    else:
        match = re.search(r"\b(?:de|a|pour)\s+(.+)$", normalized)
        city = match.group(1).strip(" ?.!	") if match else None

    if not city:
        return None
    city = _strip_filler_suffix(city)
    return city or None


def geocoding_city_name(city: str) -> str:
    """Use hyphens for multi-word city names sent to the geocoder."""
    return "-".join(city.split())


async def get_weather_answer(message: str, location: dict | None = None) -> dict:
    # Toujours renvoyer {"text": ..., "weather_type": ...} : chat.py fait response["text"] et
    # response["weather_type"] sans distinction de cas, donc une simple chaîne ici plantait en
    # TypeError ("string indices must be integers") dès qu'aucune ville n'était trouvée.
    city = extract_city(message)
    coordinates = None
    if not city and location and "latitude" in location and "longitude" in location:
        coordinates = (location["latitude"], location["longitude"])
    # Ni ville dans le message, ni position du navigateur transmise : on utilise la localisation
    # enregistrée dans Paramètres (Pays/Ville) au lieu de demander de préciser une ville — c'était
    # le bug signalé, symétrique à celui de get_time_answer ci-dessus.
    using_saved_location = not city and coordinates is None
    place_name = None
    if using_saved_location:
        coordinates = (settings.USER_LATITUDE, settings.USER_LONGITUDE)
        place_name = settings.USER_CITY_LABEL

    async with httpx.AsyncClient(timeout=8) as client:
        place = {"name": place_name or "votre position"}
        if city:
            geocoding = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": geocoding_city_name(city), "count": 1, "language": "fr", "format": "json"},
            )
            geocoding.raise_for_status()
            places = geocoding.json().get("results", [])
            if not places:
                return {"text": f"Je ne trouve pas la ville {city}.", "weather_type": None}
            place = places[0]
            coordinates = (place["latitude"], place["longitude"])
        elif not using_saved_location:
            try:
                reverse_geocoding = await client.get(
                    "https://api.bigdatacloud.net/data/reverse-geocode-client",
                    params={
                        "latitude": coordinates[0],
                        "longitude": coordinates[1],
                        "localityLanguage": "fr",
                    },
                )
                reverse_geocoding.raise_for_status()
                location_data = reverse_geocoding.json()
                place["name"] = (
                    location_data.get("city")
                    or location_data.get("locality")
                    or location_data.get("principalSubdivision")
                    or place["name"]
                )
            except (httpx.HTTPError, ValueError):
                pass

        forecast = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": coordinates[0],
                "longitude": coordinates[1],
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "timezone": "auto",
            },
        )
        forecast.raise_for_status()
        current = forecast.json()["current"]
        weather_code = current["weather_code"]
        return {
            "text": (
                f"Météo à {place['name']} : {weather_description(weather_code)}, "
                f"{current['temperature_2m']:.0f} °C, "
                f"vent {current['wind_speed_10m']:.0f} km/h."
            ),
            "weather_type": weather_icon_type(weather_code),
        }


def is_ram_request(message: str) -> bool:
    normalized = normalize_text(message)
    return "ram" in normalized or "memoire vive" in normalized or "memoire de mon pc" in normalized


def is_time_request(message: str) -> bool:
    normalized = normalize_text(message)
    if "heure" in normalized:
        return True
    return any(term in normalized for term in (
        "quelle heure",
        "heure actuelle",
        "donne l heure",
        "donner l heure",
        "dis-moi l heure",
        "dis moi l heure",
        "date du jour",
        "quelle date",
        "quelle est la date",
        "date aujourd hui",
    ))


def is_world_time_request(message: str) -> bool:
    normalized = normalize_text(message)
    return "heure monde" in normalized or "heure des capitales" in normalized or "heure g7" in normalized


def is_weather_request(message: str) -> bool:
    return "meteo" in normalize_text(message)
