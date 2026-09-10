"""Daily saint routes."""
import asyncio

from fastapi import APIRouter
from services.saint_service import get_daily_events, get_famous_birthdays, get_saint_of_day, get_weather_today

router = APIRouter()


@router.get("/today")
async def saint_of_day():
    result = get_saint_of_day()
    # Les 3 appels réseau (Wikipedia "événements", Wikipedia "naissances", météo Open-Meteo)
    # étaient enchaînés l'un après l'autre (await séquentiel) : le temps d'affichage total était
    # la SOMME des 3 requêtes, au lieu du temps du plus lent des 3 si elles partent ensemble.
    # Corrigé le 10/09/2026 (asyncio.gather) : aucune des 3 fonctions ne dépend du résultat des
    # autres (chacune ne lit que la date), rien n'empêchait de les lancer en parallèle. Chacune
    # gère déjà ses propres erreurs réseau en interne (retourne une valeur de repli au lieu de
    # lever une exception), donc gather() n'a pas besoin de return_exceptions=True ici.
    observances, famous_birthdays, weather = await asyncio.gather(
        get_daily_events(),
        get_famous_birthdays(),
        get_weather_today(),
    )
    result["observances"] = observances
    result["famous_birthdays"] = famous_birthdays
    result["weather"] = weather
    return result
