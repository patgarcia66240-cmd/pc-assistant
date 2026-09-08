"""Structured city and country facts for local chat answers."""
import asyncio
import json
import httpx
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from db import async_session, init_db
from models.conversation import CityInfoCache


CITY_PROFILES = {
    "madrid": {
        "city": "Madrid",
        "country": "Espagne",
        "country_code": "ES",
        "population": "environ 3,4 millions d'habitants",
        "area": "environ 604 km²",
        "division": "Communauté de Madrid, divisée en 21 districts municipaux",
        "country_division": "L'Espagne est organisée en 17 communautés autonomes et 2 villes autonomes.",
        "economy": "Capitale politique et économique de l'Espagne, forte dans les services, la finance, le commerce et les technologies.",
        "ethnicity": "L'Espagne ne recense pas officiellement l'appartenance ethnique. Madrid est une métropole très diverse et internationale.",
        "markets": "IBEX 35, indice principal de la Bourse espagnole de Madrid.",
        "strengths": ["centre économique et administratif", "réseau de transport dense", "patrimoine culturel et musées"],
        "weaknesses": ["étés très chauds", "pression sur les loyers", "trafic et pollution dans certaines zones"],
        "history": "Madrid est devenue la capitale permanente de l'Espagne sous Philippe II au XVIe siècle et s'est développée autour de la cour royale.",
        "position": "Centre de la péninsule Ibérique, dans la Communauté de Madrid.",
        "living_level": "Niveau de vie élevé, avec un marché de l'emploi concentré dans les services, la finance et les technologies.",
        "housing_price": "environ 3 500 à 5 000 €/m² selon le quartier",
        "comfortable_budget": "environ 1 500 à 2 200 € par mois pour une personne, logement inclus selon le quartier",
    },
    "berlin": {
        "city": "Berlin",
        "country": "Allemagne",
        "country_code": "DE",
        "population": "environ 3,9 millions d'habitants",
        "area": "environ 892 km²",
        "division": "Ville-État et capitale fédérale, divisée en 12 arrondissements",
        "country_division": "L'Allemagne est une république fédérale composée de 16 Länder.",
        "economy": "Économie avancée à revenu élevé, portée par les services, l'industrie, la recherche et l'export.",
        "ethnicity": "L'Allemagne ne publie pas de recensement officiel par appartenance ethnique. La ville est toutefois très internationale, avec de nombreuses communautés et origines.",
        "markets": "DAX (Francfort), MDAX et TecDAX ; Berlin n'a pas d'indice boursier principal propre.",
        "strengths": ["écosystème startup et recherche", "offre culturelle très riche", "transports publics et forte connectivité internationale"],
        "weaknesses": ["marché immobilier tendu", "administration parfois lente", "coût du logement en hausse"],
        "history": "Berlin est devenue capitale de l'Empire allemand en 1871, a été divisée pendant la guerre froide, puis réunifiée après la chute du mur en 1989.",
        "position": "Nord-est de l'Allemagne, sur la Spree, proche du Brandebourg.",
        "living_level": "Niveau de vie élevé et scène professionnelle internationale, mais revenus et logement varient fortement selon les quartiers.",
        "housing_price": "environ 4 500 à 7 000 €/m² selon le quartier",
        "comfortable_budget": "environ 1 700 à 2 500 € par mois pour une personne, logement inclus selon le quartier",
    },
}

MARKET_INDEXES = {
    "ES": "IBEX 35 (Madrid)",
    "FR": "CAC 40 (Paris)",
    "DE": "DAX (Francfort)",
    "GB": "FTSE 100 (Londres)",
    "IT": "FTSE MIB (Milan)",
    "US": "Dow Jones, S&P 500 et Nasdaq",
    "JP": "Nikkei 225 (Tokyo)",
}

EUROPEAN_CAPITALS = (
    ("Tirana", "AL"), ("Andorre-la-Vieille", "AD"), ("Vienne", "AT"),
    ("Minsk", "BY"), ("Bruxelles", "BE"), ("Sarajevo", "BA"),
    ("Sofia", "BG"), ("Zagreb", "HR"), ("Nicosie", "CY"),
    ("Prague", "CZ"), ("Copenhague", "DK"), ("Tallinn", "EE"),
    ("Helsinki", "FI"), ("Paris", "FR"), ("Berlin", "DE"),
    ("Athènes", "GR"), ("Budapest", "HU"), ("Reykjavik", "IS"),
    ("Dublin", "IE"), ("Rome", "IT"), ("Riga", "LV"),
    ("Vaduz", "LI"), ("Vilnius", "LT"), ("Luxembourg", "LU"),
    ("La Valette", "MT"), ("Chisinau", "MD"), ("Monaco", "MC"),
    ("Podgorica", "ME"), ("Amsterdam", "NL"), ("Skopje", "MK"),
    ("Oslo", "NO"), ("Varsovie", "PL"), ("Lisbonne", "PT"),
    ("Bucarest", "RO"), ("Moscou", "RU"), ("Saint-Marin", "SM"),
    ("Belgrade", "RS"), ("Bratislava", "SK"), ("Ljubljana", "SI"),
    ("Madrid", "ES"), ("Stockholm", "SE"), ("Berne", "CH"),
    ("Kiev", "UA"), ("Londres", "GB"), ("Cité du Vatican", "VA"),
)


def geocoding_city_name(city: str) -> str:
    """Normalize a compound city name for geocoding providers."""
    return "-".join(city.strip().split())


def format_population(value):
    if not value:
        return "Population locale indisponible"
    return f"environ {value:,}".replace(",", " ") + " habitants"


def format_area(value):
    if not value:
        return "Superficie nationale indisponible"
    return f"{value:,.0f} km²".replace(",", " ")


async def fetch_country_data(client, country_code):
    if not country_code:
        return {}
    response = await client.get(f"https://restcountries.com/v3.1/alpha/{country_code}")
    response.raise_for_status()
    return response.json()[0]


async def fetch_history(client, city):
    response = await client.get(
        f"https://fr.wikipedia.org/api/rest_v1/page/summary/{city.replace(' ', '_')}"
    )
    if response.status_code == 404:
        return "Aucun résumé historique disponible pour cette ville."
    response.raise_for_status()
    return response.json().get("extract") or "Aucun résumé historique disponible pour cette ville."


async def get_city_info(query: str) -> dict:
    normalized = query.strip().lower()
    try:
        async with async_session() as session:
            cached = await session.get(CityInfoCache, normalized)
            if cached:
                cached_data = json.loads(cached.payload)
                profile = next((value for key, value in CITY_PROFILES.items() if key in normalized), {})
                merged_data = {**profile, **cached_data}
                if merged_data != cached_data:
                    cached.payload = json.dumps(merged_data, ensure_ascii=False)
                    await session.commit()
                return merged_data
    except OperationalError:
        await init_db()

    for key, profile in CITY_PROFILES.items():
        if key in normalized:
            result = profile
            break
    else:
        result = None

    if result is not None:
        await save_city_info(normalized, result)
        return result

    city_query, separator, country_hint = query.partition(",")
    city_query = city_query.strip()
    requested_country = country_hint.strip().upper() if separator else ""

    async with httpx.AsyncClient(timeout=8) as client:
        geocoding_params = {
            "name": geocoding_city_name(city_query),
            "count": 1,
            "language": "fr",
            "format": "json",
        }
        if len(requested_country) == 2:
            geocoding_params["countryCode"] = requested_country
        response = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params=geocoding_params,
        )
        response.raise_for_status()
        places = response.json().get("results", [])
        if not places:
            raise LookupError(f"Ville introuvable: {city_query}")
        place = places[0]

        country_code = place.get("country_code", "").upper()
        country_task = fetch_country_data(client, country_code)
        history_task = fetch_history(client, place.get("name", query))
        country_data, history = await asyncio.gather(country_task, history_task, return_exceptions=True)
        if isinstance(country_data, Exception):
            country_data = {}
        if isinstance(history, Exception):
            history = "Aucun résumé historique disponible pour cette ville."

    country_name = country_data.get("translations", {}).get("fra", {}).get("common") or place.get("country", "Pays non précisé")
    city_population = place.get("population")
    country_population = country_data.get("population")
    area = country_data.get("area")
    official_name = country_data.get("name", {}).get("official", country_name)
    region = country_data.get("region", "")
    subregion = country_data.get("subregion", "")
    capital = ", ".join(country_data.get("capital", [])) or "non précisée"
    languages = ", ".join(country_data.get("languages", {}).values()) or "non précisées"
    markets = MARKET_INDEXES.get(country_code, f"Indice national de {country_name} à consulter")

    result = {
        "city": place.get("name", query.title()),
        "country": country_name,
        "country_code": country_code,
        "population": format_population(city_population),
        "area": format_area(area),
        "division": place.get("admin1", "Division administrative non précisée"),
        "country_division": f"{official_name} est situé en {region}, sous-région {subregion or 'non précisée'}. Capitale : {capital}.",
        "economy": f"Pays de {country_name} en {region.lower() or 'développement'}, avec une population nationale d'environ {country_population:,} habitants et une économie décrite par les indicateurs nationaux.".replace(",", " ") if country_population else "Indicateurs économiques nationaux indisponibles.",
        "ethnicity": f"Les données ethniques ne sont pas comparables de façon homogène. Les langues officiellement recensées sont : {languages}.",
        "markets": markets,
        "strengths": [f"capitale ou centre régional de {country_name}", f"intégration dans la région {region or 'locale'}", "patrimoine et services urbains"],
        "weaknesses": ["les indicateurs locaux détaillés peuvent varier selon la source", "coût de la vie et logement à vérifier localement"],
        "history": history,
        "position": f"Coordonnées approximatives : {place.get('latitude', 'indisponible')}, {place.get('longitude', 'indisponible')}. Région : {region or 'non précisée'}.",
        "living_level": "Niveau de vie local à comparer avec les revenus, le logement et les services du pays.",
        "housing_price": "Prix au m² indisponible pour cette ville.",
        "comfortable_budget": "Budget de vie confortable indisponible pour cette ville.",
    }
    await save_city_info(normalized, result)
    return result


async def save_city_info(query: str, data: dict) -> None:
    try:
        async with async_session() as session:
            cached = await session.get(CityInfoCache, query)
            if cached:
                cached.city = data.get("city", query)
                cached.country_code = data.get("country_code")
                cached.payload = json.dumps(data, ensure_ascii=False)
            else:
                session.add(CityInfoCache(
                    query=query,
                    city=data.get("city", query),
                    country_code=data.get("country_code"),
                    payload=json.dumps(data, ensure_ascii=False),
                ))
            await session.commit()
    except OperationalError:
        await init_db()
        async with async_session() as session:
            session.add(CityInfoCache(
                query=query,
                city=data.get("city", query),
                country_code=data.get("country_code"),
                payload=json.dumps(data, ensure_ascii=False),
            ))
            await session.commit()


async def cache_european_capitals() -> list[dict]:
    """Fetch and persist every European capital, skipping cached entries."""
    results = []
    for capital, country in EUROPEAN_CAPITALS:
        query = capital.lower()
        async with async_session() as session:
            cached = await session.get(CityInfoCache, query)
        if cached:
            results.append(json.loads(cached.payload))
            continue
        try:
            result = await get_city_info(f"{capital}, {country}")
            results.append(result)
        except (httpx.HTTPError, IndexError, KeyError, TypeError, LookupError) as error:
            results.append({"city": capital, "country_code": country, "error": type(error).__name__})
    return results


def is_city_info_request(message: str) -> bool:
    normalized = message.lower().strip()
    return normalized.startswith(("info ", "infos ", "informations ", "informations sur ", "info sur "))