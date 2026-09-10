"""Daily saint information served without an AI request."""
import json
from datetime import date, datetime, timezone
from pathlib import Path
import httpx

from config import settings

# Wikimedia bloque depuis fin août 2026 (voir meta.wikimedia.org/wiki/User-Agent_policy et
# phabricator.wikimedia.org/T400119) les requêtes sans User-Agent identifiant l'appli — httpx
# envoie sinon un User-Agent générique (ex. "python-httpx/0.27"), désormais rejeté en 403.
# Ajouté le 10/09/2026 après un 403 constaté en prod sur onthisday/events et onthisday/births.
_WIKIMEDIA_USER_AGENT = f"ARIA-PCAssistant/1.0 (usage personnel non commercial) httpx/{httpx.__version__}"
_WIKIMEDIA_HEADERS = {"User-Agent": _WIKIMEDIA_USER_AGENT}

# Calendrier complet (362/366 jours) chargé depuis backend/data/saints_calendar.json.
# Source : dataset ouvert "theofidry/ephemeris" (calendrier traditionnel des saints en
# français), complété par quelques entrées rédigées à la main pour les dates les plus
# marquantes (voir _CURATED_STORIES ci-dessous, qui prévaut sur le fichier de données).
# Avant cette modif, seules ~12 dates étaient couvertes en dur : pour toutes les autres
# (ex. le 10 septembre), l'API renvoyait un texte de repli générique ("Saint du jour"),
# ce qui donnait l'impression d'un champ vide/cassé côté frontend alors que le code
# fonctionnait : il manquait simplement la donnée. 4 dates à fête mobile (Mercredi des
# Cendres, solstices, équinoxe d'automne) sont volontairement absentes du fichier de
# données car leur date réelle varie de ±1-2 jours selon l'année : les figer serait
# afficher une fausse date certaines années, donc elles retombent sur le texte générique.
_SAINTS_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "saints_calendar.json"

with _SAINTS_DATA_PATH.open(encoding="utf-8") as _f:
    SAINTS: dict = json.load(_f)

OBSERVANCES = {
    "02-26": [{"name": "Journée nationale de la pistache", "description": "Une journée gourmande consacrée à la pistache et à ses usages culinaires."}],
    "03-08": [{"name": "Journée internationale des femmes", "description": "Une journée dédiée aux droits des femmes, à l'égalité et à la lutte contre les discriminations."}],
    "03-20": [{"name": "Journée internationale du bonheur", "description": "Une journée qui rappelle l'importance du bien-être et d'un développement plus équilibré."}],
    "04-22": [{"name": "Journée de la Terre", "description": "Une journée de sensibilisation à la protection de l'environnement et de la biodiversité."}],
    "05-01": [{"name": "Fête du Travail", "description": "Une journée consacrée aux travailleurs et aux droits sociaux."}],
    "06-05": [{"name": "Journée mondiale de l'environnement", "description": "Une journée pour promouvoir la protection de la planète et les actions écologiques."}],
    "09-08": [{"name": "Journée internationale de l'alphabétisation", "description": "Une journée qui souligne l'importance de l'accès à la lecture, à l'écriture et à l'éducation."}],
    "10-16": [{"name": "Journée mondiale de l'alimentation", "description": "Une journée consacrée à la sécurité alimentaire et à une alimentation durable."}],
    "12-10": [{"name": "Journée des droits de l'homme", "description": "Une journée qui rappelle les droits et libertés fondamentaux de chaque personne."}],
}

# Dictons météo/populaires traditionnels français, rattachés à une date précise du
# calendrier. Liste volontairement partielle (57 dates) : chaque entrée a été
# recoupée sur au moins deux sources indépendantes (nominis.cef.fr, gerbeaud.com et
# équivalents) ; les jours sans dicton bien attesté n'apparaissent pas ici plutôt que
# d'afficher quelque chose d'inventé ou d'incertain.
DICTONS = {
    "01-01": {"saint": "Saint Clair", "text": "Saint Clair porte quarantaine."},
    "01-13": {"saint": "Saint Hilaire de Poitiers", "text": "Soleil au jour de Saint Hilaire, rentre du bois pour l'hiver."},
    "01-17": {"saint": "Saint Antoine le Grand", "text": "A la Saint Antoine, les jours augmentent de la barbe d'un moine."},
    "01-20": {"saint": "Saint Sébastien", "text": "A la Saint-Sébastien, l'hiver reprend ou se casse les dents."},
    "01-22": {"saint": "Saint Vincent", "text": "Saint Vincent clair et beau, plus de vin que d'eau."},
    "01-25": {"saint": "Saint Prix", "text": "Soleil de Saint-Priest, abondance de millet."},
    "01-29": {"saint": "Saint Sulpice", "text": "S'il gèle à Saint-Sulpice, le printemps sera propice."},
    "02-02": {"saint": "Chandeleur", "text": "A la Chandeleur, l'hiver se meurt ou prend vigueur."},
    "02-03": {"saint": "Saint Blaise", "text": "Si le jour de la Saint Blaise est serein, bon temps pour le grain."},
    "02-05": {"saint": "Sainte Agathe", "text": "Si tu sèmes tes poireaux à la Sainte-Agathe, pour un brin t'en auras quatre."},
    "02-14": {"saint": "Saint Valentin", "text": "S'il ne fait froid le jour de la Saint-Valentin, vingt jours trop tôt montera la sève."},
    "02-27": {"saint": "Sainte Honorine", "text": "Gelée de Sainte-Honorine rend toute la vallée chagrine."},
    "02-28": {"saint": "Saint Romain", "text": "Soleil le dernier jour de février met des fleurs au pommier."},
    "03-01": {"saint": "Saint Aubin d'Angers", "text": "Quand il pleut à la Saint Aubin, il n'y aura ni lin ni foin."},
    "03-17": {"saint": "Saint Patrick", "text": "Sème tes pois à la Saint Patrice, tu en auras à ton caprice."},
    "03-19": {"saint": "Saint Joseph", "text": "A la Saint-Joseph beau temps, promesse de bon an."},
    "03-25": {"saint": "Annonciation", "text": "Le 25 mars passé, plus de bois amasser."},
    "04-11": {"saint": "Saint Stanislas", "text": "Avril fait la fleur, mai en a l'honneur."},
    "04-23": {"saint": "Saint Georges", "text": "A la Saint-Georges sème ton orge, à la Saint Marc il sera trop tard."},
    "04-25": {"saint": "Saint Marc", "text": "A la Saint Marc, s'il tombe de l'eau, il n'y aura pas de fruits à couteau."},
    "05-11": {"saint": "Saint Mamert", "text": "Attention, le premier des saints de glace, souvent tu en gardes la trace."},
    "05-12": {"saint": "Saint Pancrace", "text": "Saint Pancrace, Gervais et Boniface apportent souvent la glace."},
    "05-13": {"saint": "Saint Servais", "text": "Avant Saint-Servais, point d'été ; après Saint-Servais, plus de gelée."},
    "05-19": {"saint": "Saint Urbain Ier", "text": "S'il pleut à la Saint-Urbain, c'est quarante jours de pluie en chemin."},
    "06-08": {"saint": "Saint Médard", "text": "S'il pleut à la Saint-Médard, il pleut quarante jours plus tard."},
    "06-11": {"saint": "Saint Barnabé", "text": "S'il pleut à la Saint-Barnabé, il y a de l'avoine partout."},
    "06-13": {"saint": "Saint Antoine de Padoue", "text": "Saint Antoine clair et beau emplit cuves et tonneaux."},
    "06-19": {"saint": "Saints Gervais et Protais", "text": "Saint-Gervais, quand il est beau, tire Saint-Médard de l'eau."},
    "06-29": {"saint": "Saints Pierre et Paul", "text": "Saint Pierre et Paul pluvieux est pour trente jours dangereux."},
    "07-22": {"saint": "Sainte Marie-Madeleine", "text": "A la Sainte-Madeleine, les noisettes sont pleines ; à la Saint-Laurent on regarde dedans."},
    "07-26": {"saint": "Sainte Anne", "text": "S'il pleut à la Sainte Anne, c'est tout de la manne."},
    "08-10": {"saint": "Saint Laurent", "text": "Saint Laurent partage l'été par le milieu."},
    "08-11": {"saint": "Sainte Claire d'Assise", "text": "A la Sainte Claire, s'il éclaire et tonne, c'est l'annonce d'un bel automne."},
    "08-15": {"saint": "Assomption", "text": "Le quinze août, le coucou perd son chant ; c'est la caille qui le reprend."},
    "08-20": {"saint": "Saint Bernard de Clairvaux", "text": "Saint-Bernard fait mûrir les grains en retard."},
    "08-24": {"saint": "Saint Barthélemy", "text": "A la Saint-Barthélémy, la perche au noyer, le trident au fumier."},
    "08-29": {"saint": "Sainte Sabine", "text": "Quand août est pluvieux, septembre est radieux."},
    "09-01": {"saint": "Saint Gilles", "text": "S'il fait beau à la Saint-Gilles, cela durera jusqu'à la Saint-Michel."},
    "09-08": {"saint": "Nativité de la Vierge Marie", "text": "La nativité de la Vierge fait fuir les hirondelles."},
    "09-14": {"saint": "Exaltation de la Sainte-Croix", "text": "A la Sainte-Croix, cueille tes pommes et gaule tes noix."},
    "09-21": {"saint": "Saint Matthieu", "text": "A la Saint Matthieu, les jours sont égaux aux nuits dans leur cours."},
    "09-29": {"saint": "Saint Michel", "text": "Quand l'hirondelle voit la Saint Michel, l'hiver ne vient qu'à la Noël."},
    "10-01": {"saint": "Sainte Thérèse de l'Enfant-Jésus", "text": "En octobre qui ne fume bien ne récolte rien."},
    "10-04": {"saint": "Saint François d'Assise", "text": "A la Saint-François, vient le premier froid."},
    "10-09": {"saint": "Saint Denis de Paris", "text": "Beau temps à la Saint-Denis, l'hiver sera bientôt fini."},
    "10-18": {"saint": "Saint Luc", "text": "A la Saint-Luc, ne sème plus, ou sème dru."},
    "10-28": {"saint": "Saints Simon et Jude", "text": "Quand les Saints Simon et Jude n'apportent pas la pluie, celle-ci n'arrive qu'à la Sainte Cécile."},
    "11-01": {"saint": "Toussaint", "text": "Autant d'heures de soleil à la Toussaint, autant de semaines à souffler dans tes mains."},
    "11-03": {"saint": "Saint Hubert", "text": "A la Saint Hubert, les oies sauvages fuient l'hiver."},
    "11-11": {"saint": "Saint Martin de Tours", "text": "L'été de la Saint-Martin dure trois jours et un brin."},
    "11-22": {"saint": "Sainte Cécile de Rome", "text": "Pour la Sainte-Cécile, chaque fève en fait mille."},
    "11-25": {"saint": "Sainte Catherine d'Alexandrie", "text": "A la Sainte-Catherine, tout bois prend racine."},
    "11-30": {"saint": "Saint André", "text": "Neige de Saint-André peut cent jours durer."},
    "12-04": {"saint": "Sainte Barbe", "text": "Pour la Sainte Barbe, l'âne se fait la barbe."},
    "12-06": {"saint": "Saint Nicolas de Myre", "text": "Neige à la Saint Nicolas donne froid pour trois mois."},
    "12-08": {"saint": "Immaculée Conception", "text": "Jour de l'Immaculée ne se passe jamais sans gelée."},
    "12-13": {"saint": "Sainte Lucie de Syracuse", "text": "A la Sainte Luce, les jours avancent du saut d'une puce."},
    "12-25": {"saint": "Noël", "text": "Noël au balcon, Pâques au tison."},
    "12-26": {"saint": "Saint Étienne", "text": "A la Saint-Etienne, les jours croissent d'une aiguillée de laine."},
    "12-28": {"saint": "Saints Innocents", "text": "Décembre trop beau, l'été dans l'eau."},
}

# Infos complémentaires sur les prénoms (origine/signification INSEE-Super Prénom + statistiques
# de naissances officielles INSEE), chargées uniquement si le fichier existe. Ce fichier n'est PAS
# livré directement : il se construit en local, avec ta propre connexion, via
# `python backend/scripts/build_prenoms_extra.py` (voir ce script) — le sandbox de développement
# n'a pas accès aux serveurs data.gouv.fr/INSEE, donc ces données réelles doivent être
# téléchargées depuis ta machine plutôt que fabriquées ici. Tant que le script n'a pas tourné,
# cette section est simplement absente de la réponse (pas de valeur inventée en remplacement).
_PRENOMS_EXTRA_PATH = Path(__file__).resolve().parent.parent / "data" / "prenoms_extra.json"
try:
    with _PRENOMS_EXTRA_PATH.open(encoding="utf-8") as _pf:
        PRENOMS_EXTRA: dict = json.load(_pf)
except FileNotFoundError:
    PRENOMS_EXTRA = {}

FRENCH_WEEKDAYS = (
    "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"
)
FRENCH_MONTHS = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)


def format_french_date(current_day: date) -> str:
    return (
        f"{FRENCH_WEEKDAYS[current_day.weekday()]} "
        f"{current_day.day} {FRENCH_MONTHS[current_day.month - 1]} {current_day.year}"
    )


def _normalize_first_name(raw_name: str) -> str:
    """Extrait un prénom de base utilisable pour chercher dans PRENOMS_EXTRA à partir
    d'une entrée SAINTS qui peut contenir "Saint"/"Sainte", un nom composé ou un
    complément ("Sainte Marie, Mère de Dieu", "Saint Jean-Baptiste", "Saints Pierre et Paul")."""
    cleaned = raw_name
    for prefix in ("Sainte ", "Saints ", "Saint "):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    cleaned = cleaned.split(",")[0].split(" et ")[0].strip()
    return cleaned


def get_ephemeride(day: date | None = None) -> dict:
    """Position du jour dans l'année (calcul pur, exact pour toute année y compris bissextile)."""
    current_day = day or date.today()
    total_days = 366 if (current_day.year % 4 == 0 and (current_day.year % 100 != 0 or current_day.year % 400 == 0)) else 365
    day_of_year = current_day.timetuple().tm_yday
    return {
        "day_of_year": day_of_year,
        "days_remaining": total_days - day_of_year,
        "total_days_in_year": total_days,
        "week_number": int(current_day.strftime("%V")),
    }


def get_dicton(day: date | None = None) -> dict | None:
    current_day = day or date.today()
    return DICTONS.get(current_day.strftime("%m-%d"))


def get_prenom_info(saint_name: str) -> dict | None:
    if not PRENOMS_EXTRA:
        return None
    base = _normalize_first_name(saint_name)
    entry = PRENOMS_EXTRA.get(base) or PRENOMS_EXTRA.get(base.lower())
    if entry is None:
        return None
    # Le frontend affiche "Le prénom {prenom}" sans avoir à ré-analyser saint_name lui-même.
    return {"prenom": base, **entry}


def get_saint_of_day(day: date | None = None) -> dict:
    current_day = day or date.today()
    key = current_day.strftime("%m-%d")
    saint = SAINTS.get(key, {
        "name": "Saint du jour",
        "story": "La fiche détaillée de cette date sera bientôt enrichie.",
    })
    return {
        "date": current_day.isoformat(),
        "display_date": format_french_date(current_day),
        **saint,
        "observances": OBSERVANCES.get(key, []),
        "ephemeride": get_ephemeride(current_day),
        "dicton": get_dicton(current_day),
        "prenom_info": get_prenom_info(saint["name"]),
        "moon_phase": get_moon_phase(current_day),
        "next_holiday": get_next_public_holiday(current_day),
    }


async def get_daily_events(day: date | None = None) -> list[dict]:
    current_day = day or date.today()
    local_events = OBSERVANCES.get(current_day.strftime("%m-%d"), [])
    if local_events:
        return local_events

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                f"https://fr.wikipedia.org/api/rest_v1/feed/onthisday/events/{current_day.month:02d}/{current_day.day:02d}",
                headers=_WIKIMEDIA_HEADERS,
            )
            response.raise_for_status()
            events = response.json().get("events", [])[:3]
            return [
                {
                    "name": event.get("text", "Événement historique"),
                    "description": f"Événement du {event.get('year', '')} dans l'histoire.",
                }
                for event in events
            ] or [{"name": "Repère du jour", "description": "Aucun événement historique détaillé n'est disponible pour cette date."}]
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return [{"name": "Repère du jour", "description": "Une date à découvrir dans l'histoire et la culture."}]


async def get_famous_birthdays(day: date | None = None, limit: int = 5) -> list[dict]:
    """Personnalités nées ce jour-là (n'importe quelle année), via l'API Wikimedia
    "on this day / births" (même service, même fiabilité que get_daily_events ci-dessus,
    déjà utilisé dans l'app). Aucune donnée statique ici : si l'appel échoue (pas de
    réseau, API indisponible), on renvoie une liste vide plutôt qu'un nom inventé."""
    current_day = day or date.today()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                f"https://fr.wikipedia.org/api/rest_v1/feed/onthisday/births/{current_day.month:02d}/{current_day.day:02d}",
                headers=_WIKIMEDIA_HEADERS,
            )
            response.raise_for_status()
            births = response.json().get("births", [])
            results = []
            for entry in births:
                text = entry.get("text", "").strip()
                year = entry.get("year")
                if not text or year is None:
                    continue
                results.append({"name": text, "year": year})
            # Les plus récents en premier (plus susceptibles d'être reconnus).
            results.sort(key=lambda item: item["year"], reverse=True)
            return results[:limit]
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return []


# --- Phase de la lune -------------------------------------------------------------------
# Calcul astronomique pur (pas d'API, pas de donnée statique) : distance en jours à une
# nouvelle lune de référence connue, divisée par la durée moyenne d'un cycle synodique.
# Référence utilisée : nouvelle lune du 24 janvier 2001 à 13h07 UTC (AstroPixels, catalogue
# des phases lunaires 2001-2100 - astropixels.com/ephemeris/phasescat/phases2001.html),
# vérifiée en la recoupant avec les 11 autres nouvelles lunes listées pour 2001 : l'écart
# entre la prédiction du modèle linéaire et l'heure réelle reste sous ~14h sur toute
# l'année, largement dans la marge d'une "case" de phase (~3,7 jours) - donc fiable pour
# nommer la phase, pas pour une heure exacte de nouvelle/pleine lune à la minute près.
_MOON_REFERENCE_NEW_MOON = datetime(2001, 1, 24, 13, 7, tzinfo=timezone.utc)
_SYNODIC_MONTH_DAYS = 29.530588853

_MOON_PHASES = (
    ("Nouvelle lune", "🌑"),
    ("Premier croissant", "🌒"),
    ("Premier quartier", "🌓"),
    ("Lune gibbeuse croissante", "🌔"),
    ("Pleine lune", "🌕"),
    ("Lune gibbeuse décroissante", "🌖"),
    ("Dernier quartier", "🌗"),
    ("Dernier croissant", "🌘"),
)


def get_moon_phase(day: date | None = None) -> dict:
    current_day = day or date.today()
    moment = datetime(current_day.year, current_day.month, current_day.day, 12, tzinfo=timezone.utc)
    days_since_ref = (moment - _MOON_REFERENCE_NEW_MOON).total_seconds() / 86400
    age_days = days_since_ref % _SYNODIC_MONTH_DAYS
    fraction = age_days / _SYNODIC_MONTH_DAYS
    index = int(fraction * 8) % 8
    name, emoji = _MOON_PHASES[index]
    return {"name": name, "emoji": emoji, "age_days": round(age_days, 1)}


# --- Prochain jour férié -----------------------------------------------------------------
def _easter_date(year: int) -> date:
    """Algorithme anonyme grégorien (Meeus/Jones/Butcher) de calcul de la date de Pâques.
    Vérifié contre une source externe pour 2026 (5 avril, joursferies.fr) et contre les
    dates 2024/2025 déjà connues (31 mars / 20 avril)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day_of_month = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day_of_month)


def _public_holidays(year: int) -> list[tuple[date, str]]:
    easter = _easter_date(year)
    from datetime import timedelta
    return [
        (date(year, 1, 1), "Jour de l'An"),
        (easter, "Pâques"),
        (easter + timedelta(days=1), "Lundi de Pâques"),
        (date(year, 5, 1), "Fête du Travail"),
        (date(year, 5, 8), "Victoire 1945"),
        (easter + timedelta(days=39), "Ascension"),
        (easter + timedelta(days=50), "Lundi de Pentecôte"),
        (date(year, 7, 14), "Fête Nationale"),
        (date(year, 8, 15), "Assomption"),
        (date(year, 11, 1), "Toussaint"),
        (date(year, 11, 11), "Armistice 1918"),
        (date(year, 12, 25), "Noël"),
    ]


def get_next_public_holiday(day: date | None = None) -> dict:
    current_day = day or date.today()
    if current_day in dict(_public_holidays(current_day.year)):
        name = dict(_public_holidays(current_day.year))[current_day]
        return {"name": name, "date": current_day.isoformat(), "days_until": 0, "is_today": True}

    candidates = sorted(
        (d, name)
        for d, name in _public_holidays(current_day.year) + _public_holidays(current_day.year + 1)
        if d > current_day
    )
    next_date, next_name = candidates[0]
    return {
        "name": next_name,
        "date": next_date.isoformat(),
        "days_until": (next_date - current_day).days,
        "is_today": False,
    }


# --- Météo du jour -----------------------------------------------------------------------
# Code Open-Meteo (WMO Weather interpretation codes, table standard documentée par
# open-meteo.com/en/docs) -> libellé français court.
_WEATHER_CODE_LABELS = {
    0: "Ciel dégagé", 1: "Plutôt dégagé", 2: "Partiellement nuageux", 3: "Couvert",
    45: "Brouillard", 48: "Brouillard givrant",
    51: "Bruine légère", 53: "Bruine modérée", 55: "Bruine dense",
    56: "Bruine verglaçante légère", 57: "Bruine verglaçante dense",
    61: "Pluie légère", 63: "Pluie modérée", 65: "Pluie forte",
    66: "Pluie verglaçante légère", 67: "Pluie verglaçante forte",
    71: "Neige légère", 73: "Neige modérée", 75: "Neige forte", 77: "Grains de neige",
    80: "Averses légères", 81: "Averses modérées", 82: "Averses violentes",
    85: "Averses de neige légères", 86: "Averses de neige fortes",
    95: "Orage", 96: "Orage avec grêle légère", 99: "Orage avec grêle forte",
}


async def get_weather_today() -> dict | None:
    """Météo du jour pour la ville configurée (USER_LATITUDE/USER_LONGITUDE dans config.py),
    via Open-Meteo (API publique, gratuite, sans clé - open-meteo.com). Appel en direct à
    chaque requête, pas de cache/donnée statique. Si l'appel échoue (pas de réseau, API
    indisponible), on renvoie None : la section est alors simplement absente côté frontend,
    jamais remplie avec une météo inventée."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": settings.USER_LATITUDE,
                    "longitude": settings.USER_LONGITUDE,
                    "current": "temperature_2m,weather_code",
                    "daily": "sunrise,sunset,temperature_2m_max,temperature_2m_min",
                    "timezone": "auto",
                    "forecast_days": 1,
                },
            )
            response.raise_for_status()
            payload = response.json()
            current = payload.get("current", {})
            daily = payload.get("daily", {})
            code = current.get("weather_code")
            return {
                "city": settings.USER_CITY_LABEL,
                "temperature": current.get("temperature_2m"),
                "temperature_max": (daily.get("temperature_2m_max") or [None])[0],
                "temperature_min": (daily.get("temperature_2m_min") or [None])[0],
                "condition": _WEATHER_CODE_LABELS.get(code, "Conditions variables"),
                "sunrise": (daily.get("sunrise") or [None])[0],
                "sunset": (daily.get("sunset") or [None])[0],
            }
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return None
