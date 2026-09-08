"""Daily saint information served without an AI request."""
from datetime import date
import httpx

SAINTS = {
    "01-01": {
        "name": "Sainte Marie, Mère de Dieu",
        "story": "Cette fête ouvre l'année chrétienne en honorant Marie comme mère de Jésus et figure de paix.",
    },
    "02-02": {
        "name": "Sainte Présentation du Seigneur",
        "story": "La Présentation rappelle l'offrande de Jésus au Temple et la rencontre avec Syméon et Anne.",
    },
    "03-19": {
        "name": "Saint Joseph",
        "story": "Saint Joseph est présenté comme l'artisan de Nazareth et le protecteur attentif de la famille de Jésus.",
    },
    "04-23": {
        "name": "Saint Georges",
        "story": "Saint Georges est une figure de courage, traditionnellement associé à la victoire du bien sur le mal.",
    },
    "05-01": {
        "name": "Saint Joseph travailleur",
        "story": "Cette journée met à l'honneur le travail humble et la dignité de chaque métier, à l'image de Joseph.",
    },
    "06-24": {
        "name": "Saint Jean-Baptiste",
        "story": "Jean-Baptiste est le prophète qui annonce la venue du Christ et invite à préparer les chemins.",
    },
    "07-14": {
        "name": "Saint Camille de Lellis",
        "story": "Camille de Lellis consacra sa vie aux malades et fonda une communauté dédiée au soin des personnes fragiles.",
    },
    "08-15": {
        "name": "Sainte Marie",
        "story": "La fête de l'Assomption célèbre Marie et son élévation auprès de Dieu selon la tradition chrétienne.",
    },
    "09-08": {
        "name": "La Nativité de la Vierge Marie",
        "story": "Cette fête célèbre la naissance de Marie. Elle rappelle son rôle dans l'histoire chrétienne et son importance dans la tradition mariale.",
    },
    "10-01": {
        "name": "Sainte Thérèse de Lisieux",
        "story": "Thérèse de Lisieux est connue pour sa confiance, sa simplicité et sa spiritualité de la petite voie.",
    },
    "11-01": {
        "name": "Tous les Saints",
        "story": "La Toussaint célèbre tous les saints connus et inconnus, témoins de vie et d'espérance dans la tradition chrétienne.",
    },
    "12-25": {
        "name": "La Nativité du Seigneur",
        "story": "Noël célèbre la naissance de Jésus à Bethléem et le message de paix associé à cet événement.",
    },
}

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
    }


async def get_daily_events(day: date | None = None) -> list[dict]:
    current_day = day or date.today()
    local_events = OBSERVANCES.get(current_day.strftime("%m-%d"), [])
    if local_events:
        return local_events

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                f"https://fr.wikipedia.org/api/rest_v1/feed/onthisday/events/{current_day.month:02d}/{current_day.day:02d}"
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