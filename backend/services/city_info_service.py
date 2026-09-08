"""Structured city and country facts for local chat answers."""
import asyncio
import csv
import io
import json
import logging
import re
import statistics
import httpx
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from db import async_session, init_db
from models.conversation import CityInfoCache

logger = logging.getLogger(__name__)

# Wikipedia (comme la plupart des API Wikimedia) rejette les requêtes sans User-Agent
# descriptif (403 Forbidden) — cf. https://meta.wikimedia.org/wiki/User-Agent_policy.
HTTP_HEADERS = {
    "User-Agent": "PC-Assistant-ARIA/0.1 (assistant personnel local ; "
    "https://github.com/patgarcia66240-cmd/pc-assistant)"
}

# restcountries.com a totalement retiré son ancienne API v3.1 (gratuite, sans clé) : elle
# redirige maintenant vers une v5 qui exige une clé payante/gratuite avec inscription. En
# attendant une décision sur ce remplacement, on évite l'appel réseau pour la France (qui
# ne change pratiquement jamais) avec des faits fixes, revérifiés à la main :
# population au 1er janvier 2026 source INSEE (bilan démographique 2025, insee.fr/fr/statistiques/8719824).
FRANCE_COUNTRY_FACTS = {
    "translations": {"fra": {"common": "France"}},
    "name": {"official": "République française"},
    "population": 69_100_000,
    "area": 551_695,
    "region": "Europe",
    "subregion": "Europe de l'Ouest",
    "capital": ["Paris"],
    "languages": {"fra": "Français"},
}


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
        "places_to_visit": "Musée du Prado, Parc du Retiro, Palais Royal, Plaza Mayor, Puerta del Sol.",
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
        "places_to_visit": "Porte de Brandebourg, Île aux musées, Reichstag, East Side Gallery, Alexanderplatz.",
        "strengths": ["écosystème startup et recherche", "offre culturelle très riche", "transports publics et forte connectivité internationale"],
        "weaknesses": ["marché immobilier tendu", "administration parfois lente", "coût du logement en hausse"],
        "history": "Berlin est devenue capitale de l'Empire allemand en 1871, a été divisée pendant la guerre froide, puis réunifiée après la chute du mur en 1989.",
        "position": "Nord-est de l'Allemagne, sur la Spree, proche du Brandebourg.",
        "living_level": "Niveau de vie élevé et scène professionnelle internationale, mais revenus et logement varient fortement selon les quartiers.",
        "housing_price": "environ 4 500 à 7 000 €/m² selon le quartier",
        "comfortable_budget": "environ 1 700 à 2 500 € par mois pour une personne, logement inclus selon le quartier",
    },
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
        return "Superficie indisponible"
    return f"{value:,.0f} km²".replace(",", " ")


async def fetch_country_data(client, country_code):
    if not country_code:
        return {}
    if country_code == "FR":
        # restcountries.com v3.1 est mort (redirige vers une v5 payante/sur inscription) :
        # pour la France, des faits fixes évitent un appel réseau voué à échouer.
        return FRANCE_COUNTRY_FACTS
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


async def fetch_nearby_landmarks(client, city_name, lat, lon):
    """Lieux/monuments notables à proximité, via l'API de géo-recherche Wikipedia (list=geosearch),
    cf. https://www.mediawiki.org/wiki/API:Geosearch et l'exemple officiel Wikimedia
    https://github.com/martyav/MediaWiki-Action-API-Code-Samples/blob/master/python/geosearch.py"""
    if lat is None or lon is None:
        return []
    response = await client.get(
        "https://fr.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "geosearch",
            "gscoord": f"{lat}|{lon}",
            "gsradius": 10000,
            "gslimit": 8,
            "format": "json",
        },
    )
    response.raise_for_status()
    places = response.json().get("query", {}).get("geosearch", [])
    normalized_city = (city_name or "").strip().lower()
    return [
        place["title"] for place in places
        if place.get("title") and place["title"].strip().lower() != normalized_city
    ]


async def fetch_french_commune_data(client, city_name):
    """Real, commune-level facts (population, superficie, département, région) via l'API officielle geo.api.gouv.fr."""
    response = await client.get(
        "https://geo.api.gouv.fr/communes",
        params={
            "nom": city_name,
            "fields": "departement,region,population,surface,codesPostaux",
            "format": "json",
            "boost": "population",
            "limit": 1,
        },
    )
    response.raise_for_status()
    results = response.json()
    return results[0] if results else {}


# Niveau de vie médian et taux de pauvreté par département (Filosofi 2023,
# INSEE-DGFiP-Cnaf-Cnav-CCMSA), obtenus via l'API Melodi de l'Insee (dataset
# DS_FILOSOFI_SAGE_LOG_TP_NIVVIE_2023, accès libre sans inscription/clé).
# Le Filosofi n'est pas diffusé à l'échelle de la commune sans une clé API
# dédiée : le département est la maille géographique fiable la plus fine
# disponible gratuitement.
DEP_NIVEAU_DE_VIE_2023 = {
    "01": {"median": 27990, "poverty_rate": 12.2},
    "02": {"median": 23360, "poverty_rate": 19.4},
    "03": {"median": 24430, "poverty_rate": 16.4},
    "04": {"median": 24240, "poverty_rate": 18.6},
    "05": {"median": 25060, "poverty_rate": 14.3},
    "06": {"median": 26380, "poverty_rate": 17.7},
    "07": {"median": 24820, "poverty_rate": 15.6},
    "08": {"median": 23500, "poverty_rate": 19.9},
    "09": {"median": 23360, "poverty_rate": 20.0},
    "10": {"median": 24130, "poverty_rate": 18.1},
    "11": {"median": 23060, "poverty_rate": 21.2},
    "12": {"median": 24780, "poverty_rate": 14.5},
    "13": {"median": 25610, "poverty_rate": 20.3},
    "14": {"median": 25600, "poverty_rate": 13.5},
    "15": {"median": 24820, "poverty_rate": 13.7},
    "16": {"median": 24850, "poverty_rate": 15.4},
    "17": {"median": 25710, "poverty_rate": 13.1},
    "18": {"median": 24730, "poverty_rate": 15.9},
    "19": {"median": 24910, "poverty_rate": 14.4},
    "21": {"median": 26560, "poverty_rate": 13.0},
    "22": {"median": 25590, "poverty_rate": 12.2},
    "23": {"median": 23210, "poverty_rate": 19.5},
    "24": {"median": 24150, "poverty_rate": 17.1},
    "25": {"median": 27190, "poverty_rate": 13.4},
    "26": {"median": 25210, "poverty_rate": 16.0},
    "27": {"median": 25520, "poverty_rate": 13.8},
    "28": {"median": 25980, "poverty_rate": 13.3},
    "29": {"median": 26210, "poverty_rate": 11.4},
    "2A": {"median": 26050, "poverty_rate": 17.9},
    "2B": {"median": 24200, "poverty_rate": 21.8},
    "30": {"median": 23930, "poverty_rate": 21.0},
    "31": {"median": 27040, "poverty_rate": 15.9},
    "32": {"median": 24770, "poverty_rate": 15.6},
    "33": {"median": 26820, "poverty_rate": 14.2},
    "34": {"median": 24280, "poverty_rate": 21.0},
    "35": {"median": 26670, "poverty_rate": 11.7},
    "36": {"median": 24020, "poverty_rate": 15.8},
    "37": {"median": 25930, "poverty_rate": 14.1},
    "38": {"median": 27290, "poverty_rate": 13.0},
    "39": {"median": 26090, "poverty_rate": 12.3},
    "40": {"median": 25650, "poverty_rate": 12.1},
    "41": {"median": 25240, "poverty_rate": 14.0},
    "42": {"median": 24800, "poverty_rate": 16.8},
    "43": {"median": 25140, "poverty_rate": 12.4},
    "44": {"median": 27150, "poverty_rate": 11.5},
    "45": {"median": 25800, "poverty_rate": 15.0},
    "46": {"median": 24740, "poverty_rate": 15.8},
    "47": {"median": 23730, "poverty_rate": 18.5},
    "48": {"median": 24270, "poverty_rate": 15.3},
    "49": {"median": 25550, "poverty_rate": 11.8},
    "50": {"median": 25430, "poverty_rate": 12.0},
    "51": {"median": 25700, "poverty_rate": 15.8},
    "52": {"median": 23980, "poverty_rate": 16.0},
    "53": {"median": 25140, "poverty_rate": 11.6},
    "54": {"median": 25910, "poverty_rate": 16.1},
    "55": {"median": 24740, "poverty_rate": 15.0},
    "56": {"median": 26250, "poverty_rate": 11.3},
    "57": {"median": 26030, "poverty_rate": 16.6},
    "58": {"median": 24010, "poverty_rate": 17.3},
    "59": {"median": 23810, "poverty_rate": 20.7},
    "60": {"median": 25970, "poverty_rate": 14.5},
    "61": {"median": 24110, "poverty_rate": 16.3},
    "62": {"median": 23260, "poverty_rate": 19.1},
    "63": {"median": 26040, "poverty_rate": 14.8},
    "64": {"median": 26300, "poverty_rate": 13.3},
    "65": {"median": 24320, "poverty_rate": 16.6},
    "66": {"median": 23080, "poverty_rate": 22.4},
    "67": {"median": 26890, "poverty_rate": 15.0},
    "68": {"median": 27620, "poverty_rate": 14.1},
    "69": {"median": 27500, "poverty_rate": 16.3},
    "70": {"median": 24750, "poverty_rate": 13.8},
    "71": {"median": 24970, "poverty_rate": 14.1},
    "72": {"median": 24990, "poverty_rate": 14.1},
    "73": {"median": 27910, "poverty_rate": 11.1},
    "74": {"median": 32180, "poverty_rate": 10.2},
    "75": {"median": 33650, "poverty_rate": 16.8},
    "76": {"median": 24940, "poverty_rate": 16.6},
    "77": {"median": 27480, "poverty_rate": 13.6},
    "78": {"median": 31520, "poverty_rate": 11.6},
    "79": {"median": 25080, "poverty_rate": 12.7},
    "80": {"median": 24200, "poverty_rate": 17.3},
    "81": {"median": 24420, "poverty_rate": 16.4},
    "82": {"median": 24350, "poverty_rate": 17.0},
    "83": {"median": 25940, "poverty_rate": 16.8},
    "84": {"median": 23840, "poverty_rate": 21.4},
    "85": {"median": 25850, "poverty_rate": 9.2},
    "86": {"median": 24940, "poverty_rate": 15.5},
    "87": {"median": 24740, "poverty_rate": 17.1},
    "88": {"median": 24320, "poverty_rate": 15.8},
    "89": {"median": 24590, "poverty_rate": 16.0},
    "90": {"median": 25910, "poverty_rate": 17.1},
    "91": {"median": 27940, "poverty_rate": 15.4},
    "92": {"median": 33790, "poverty_rate": 13.5},
    "93": {"median": 21250, "poverty_rate": 29.5},
    "94": {"median": 27250, "poverty_rate": 18.4},
    "95": {"median": 25890, "poverty_rate": 19.4},
    "974": {"median": 19110, "poverty_rate": 36.4},
}


def _format_euros(value):
    return f"{value:,}".replace(",", " ")


def format_niveau_de_vie(departement):
    """Niveau de vie médian réel (Filosofi 2023, moyenne départementale) pour une commune française."""
    code = (departement or {}).get("code")
    stats = DEP_NIVEAU_DE_VIE_2023.get(code)
    if not stats:
        return "Niveau de vie local à comparer avec les revenus, le logement et les services du pays."
    nom = departement.get("nom", "")
    median_annuel = stats["median"]
    median_mensuel = round(median_annuel / 12)
    return (
        f"Niveau de vie médian dans le département {nom} ({code}) : environ {_format_euros(median_mensuel)} €/mois "
        f"({_format_euros(median_annuel)} €/an), taux de pauvreté {stats['poverty_rate']} % "
        f"(INSEE Filosofi 2023, moyenne départementale — donnée communale non disponible sans clé API dédiée)."
    )


def format_comfortable_budget(departement):
    """Budget mensuel repère pour une personne seule, calculé à partir du niveau de vie médian
    départemental (Filosofi 2023) : le seuil de pauvreté (définition officielle Insee/Eurostat,
    60 % du niveau de vie médian) sert de repère bas, le niveau de vie médian lui-même de repère
    pour un budget "correct" (une personne au niveau de vie médian est par définition dans la
    moitié la mieux lotie de la population locale). Pas de coefficient inventé : les deux seuils
    viennent de données réelles et d'une définition standard, pas d'une estimation arbitraire."""
    code = (departement or {}).get("code")
    stats = DEP_NIVEAU_DE_VIE_2023.get(code)
    if not stats:
        return "Budget de vie confortable non disponible (aucune source vérifiée connectée pour cette donnée)."
    nom = departement.get("nom", "")
    median_annuel = stats["median"]
    median_mensuel = round(median_annuel / 12)
    seuil_pauvrete_mensuel = round(median_annuel * 0.6 / 12)
    return (
        f"Pour une personne seule dans le département {nom} ({code}) : au moins "
        f"{_format_euros(seuil_pauvrete_mensuel)} €/mois pour rester au-dessus du seuil de pauvreté local "
        f"(60 % du niveau de vie médian, définition Insee/Eurostat), et environ "
        f"{_format_euros(median_mensuel)} €/mois pour se situer au niveau de vie médian local "
        f"(INSEE Filosofi 2023, moyenne départementale — donnée communale non disponible sans clé API dédiée)."
    )


# Niveau de vie médian et taux de pauvreté par région (Filosofi 2023, même source et mêmes
# réserves que DEP_NIVEAU_DE_VIE_2023 ci-dessus — dataset DS_FILOSOFI_SAGE_LOG_TP_NIVVIE_2023).
REG_NIVEAU_DE_VIE_2023 = {
    "04": {"median": 19110, "poverty_rate": 36.4},
    "11": {"median": 28210, "poverty_rate": 17.3},
    "24": {"median": 25490, "poverty_rate": 14.5},
    "27": {"median": 25640, "poverty_rate": 14.2},
    "28": {"median": 25200, "poverty_rate": 14.7},
    "32": {"median": 23950, "poverty_rate": 19.0},
    "44": {"median": 25850, "poverty_rate": 15.9},
    "52": {"median": 26040, "poverty_rate": 11.5},
    "53": {"median": 26240, "poverty_rate": 11.6},
    "75": {"median": 25520, "poverty_rate": 14.6},
    "76": {"median": 24650, "poverty_rate": 18.6},
    "84": {"median": 26920, "poverty_rate": 14.2},
    "93": {"median": 25560, "poverty_rate": 18.9},
    "94": {"median": 25020, "poverty_rate": 20.0},
}


def format_niveau_de_vie_echelle(nom, code, stats, echelle):
    """Version générique de format_niveau_de_vie pour un département ou une région
    (echelle = "dans le département" ou "dans la région")."""
    if not stats:
        return "Niveau de vie non disponible (donnée Insee Filosofi manquante pour cette zone)."
    median_annuel = stats["median"]
    median_mensuel = round(median_annuel / 12)
    return (
        f"Niveau de vie médian {echelle} {nom} ({code}) : environ {_format_euros(median_mensuel)} €/mois "
        f"({_format_euros(median_annuel)} €/an), taux de pauvreté {stats['poverty_rate']} % (INSEE Filosofi 2023)."
    )


def format_comfortable_budget_echelle(nom, code, stats, echelle):
    """Version générique de format_comfortable_budget pour un département ou une région."""
    if not stats:
        return "Budget de vie confortable non disponible (donnée Insee Filosofi manquante pour cette zone)."
    median_annuel = stats["median"]
    median_mensuel = round(median_annuel / 12)
    seuil_pauvrete_mensuel = round(median_annuel * 0.6 / 12)
    return (
        f"Pour une personne seule {echelle} {nom} ({code}) : au moins "
        f"{_format_euros(seuil_pauvrete_mensuel)} €/mois pour rester au-dessus du seuil de pauvreté "
        f"(60 % du niveau de vie médian, définition Insee/Eurostat), et environ "
        f"{_format_euros(median_mensuel)} €/mois pour se situer au niveau de vie médian "
        f"(INSEE Filosofi 2023)."
    )


async def resolve_departement(client, query):
    """Résout un nom ou un code de département vers ses infos officielles (geo.api.gouv.fr)."""
    q = query.strip()
    if re.fullmatch(r"\d{1,3}", q) or re.fullmatch(r"2[ab]", q, flags=re.IGNORECASE):
        code = q.upper() if q[:1] == "2" and len(q) == 2 else q.zfill(2)
        response = await client.get(f"https://geo.api.gouv.fr/departements/{code}")
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        dept = response.json()
    else:
        response = await client.get("https://geo.api.gouv.fr/departements", params={"nom": q})
        response.raise_for_status()
        results = response.json()
        if not results:
            return {}
        dept = results[0]
    region_nom = None
    if dept.get("codeRegion"):
        region_response = await client.get(f"https://geo.api.gouv.fr/regions/{dept['codeRegion']}")
        if region_response.status_code != 404:
            region_response.raise_for_status()
            region_nom = region_response.json().get("nom")
    return {"code": dept["code"], "nom": dept["nom"], "region_code": dept.get("codeRegion"), "region_nom": region_nom}


async def resolve_region(client, query):
    """Résout un nom ou un code de région vers ses infos officielles (geo.api.gouv.fr)."""
    q = query.strip()
    if q.isdigit():
        response = await client.get(f"https://geo.api.gouv.fr/regions/{q}")
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        region = response.json()
    else:
        response = await client.get("https://geo.api.gouv.fr/regions", params={"nom": q})
        response.raise_for_status()
        results = response.json()
        if not results:
            return {}
        region = results[0]
    return {"code": region.get("code"), "nom": region.get("nom")}


async def fetch_departement_communes_stats(client, dept_code):
    """Agrège population et superficie réelles sur toutes les communes d'un département
    (geo.api.gouv.fr, "surface" en hectares — converti en km²)."""
    response = await client.get(
        f"https://geo.api.gouv.fr/departements/{dept_code}/communes",
        params={"fields": "nom,population,surface"},
    )
    response.raise_for_status()
    communes = response.json()
    population_total = sum(c.get("population") or 0 for c in communes)
    surface_total_km2 = sum((c.get("surface") or 0) for c in communes) / 100
    largest = max(communes, key=lambda c: c.get("population") or 0, default=None)
    return {
        "population": population_total,
        "surface_km2": surface_total_km2,
        "largest_city": largest.get("nom") if largest else None,
        "largest_city_population": largest.get("population") if largest else None,
        "nb_communes": len(communes),
    }


async def fetch_region_communes_stats(client, dept_codes):
    """Agrège population/superficie sur tous les départements d'une région : geo.api.gouv.fr
    n'a pas d'endpoint /regions/{code}/communes direct, donc on additionne les départements."""
    tasks = [fetch_departement_communes_stats(client, code) for code in dept_codes]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    population_total, surface_total, nb_communes = 0, 0.0, 0
    largest_city, largest_pop = None, -1
    for r in results:
        if isinstance(r, Exception):
            continue
        population_total += r["population"]
        surface_total += r["surface_km2"]
        nb_communes += r["nb_communes"]
        if (r["largest_city_population"] or -1) > largest_pop:
            largest_pop = r["largest_city_population"] or -1
            largest_city = r["largest_city"]
    return {
        "population": population_total,
        "surface_km2": surface_total,
        "largest_city": largest_city,
        "largest_city_population": largest_pop if largest_pop >= 0 else None,
        "nb_communes": nb_communes,
    }


def _format_largest_city(stats):
    if not stats.get("largest_city"):
        return "Non disponible"
    return f"{stats['largest_city']} (environ {_format_euros(stats['largest_city_population'] or 0)} habitants)"


async def fetch_departement_info(query: str) -> dict:
    """Fiche département : identité, population/superficie réelles (agrégées commune par
    commune via geo.api.gouv.fr), niveau de vie et budget (Filosofi 2023), historique (Wikipédia)."""
    async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers=HTTP_HEADERS) as client:
        dept = await resolve_departement(client, query)
        if not dept:
            raise LookupError(f"Département introuvable : {query}")
        gathered = await asyncio.gather(
            fetch_history(client, dept["nom"]),
            fetch_departement_communes_stats(client, dept["code"]),
            return_exceptions=True,
        )
    history, stats = gathered
    if isinstance(history, Exception):
        logger.warning("fetch_history(%s) a échoué : %r", dept["nom"], history)
        history = "Aucun résumé historique disponible pour ce département."
    if isinstance(stats, Exception):
        logger.warning("fetch_departement_communes_stats(%s) a échoué : %r", dept["code"], stats)
        stats = {"population": None, "surface_km2": None, "largest_city": None, "largest_city_population": None, "nb_communes": None}

    niveau_stats = DEP_NIVEAU_DE_VIE_2023.get(dept["code"])
    result = {
        "kind": "departement",
        "city": dept["nom"],
        "nom": dept["nom"],
        "code": dept["code"],
        "parent_label": f"Région : {dept['region_nom']}" if dept.get("region_nom") else "Région non précisée",
        "population": format_population(stats.get("population")),
        "area": format_area(stats.get("surface_km2")),
        "nb_communes": stats.get("nb_communes") or "Non disponible",
        "largest_city": _format_largest_city(stats),
        "history": history,
        "living_level": format_niveau_de_vie_echelle(dept["nom"], dept["code"], niveau_stats, "dans le département"),
        "comfortable_budget": format_comfortable_budget_echelle(dept["nom"], dept["code"], niveau_stats, "dans le département"),
    }
    await save_city_info(f"dep:{dept['code']}", result)
    return result


async def fetch_region_info(query: str) -> dict:
    """Fiche région : identité, population/superficie réelles (agrégées via tous les
    départements de la région), niveau de vie et budget (Filosofi 2023), historique (Wikipédia)."""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=HTTP_HEADERS) as client:
        region = await resolve_region(client, query)
        if not region:
            raise LookupError(f"Région introuvable : {query}")
        depts_response = await client.get(f"https://geo.api.gouv.fr/regions/{region['code']}/departements")
        depts_response.raise_for_status()
        depts = depts_response.json()
        dept_codes = [d["code"] for d in depts]
        gathered = await asyncio.gather(
            fetch_history(client, region["nom"]),
            fetch_region_communes_stats(client, dept_codes),
            return_exceptions=True,
        )
    history, stats = gathered
    if isinstance(history, Exception):
        logger.warning("fetch_history(%s) a échoué : %r", region["nom"], history)
        history = "Aucun résumé historique disponible pour cette région."
    if isinstance(stats, Exception):
        logger.warning("fetch_region_communes_stats(%s) a échoué : %r", region["code"], stats)
        stats = {"population": None, "surface_km2": None, "largest_city": None, "largest_city_population": None, "nb_communes": None}

    niveau_stats = REG_NIVEAU_DE_VIE_2023.get(region["code"])
    result = {
        "kind": "region",
        "city": region["nom"],
        "nom": region["nom"],
        "code": region["code"],
        "parent_label": f"Départements : {', '.join(d['nom'] for d in depts)}" if depts else "Départements non précisés",
        "population": format_population(stats.get("population")),
        "area": format_area(stats.get("surface_km2")),
        "nb_communes": stats.get("nb_communes") or "Non disponible",
        "largest_city": _format_largest_city(stats),
        "history": history,
        "living_level": format_niveau_de_vie_echelle(region["nom"], region["code"], niveau_stats, "dans la région"),
        "comfortable_budget": format_comfortable_budget_echelle(region["nom"], region["code"], niveau_stats, "dans la région"),
    }
    await save_city_info(f"reg:{region['code']}", result)
    return result


def is_departement_info_request(message: str) -> bool:
    return bool(re.match(r"^(?:infos?|informations?)\s+d[ée]partements?\s+\S", message.strip(), flags=re.IGNORECASE))


def is_region_info_request(message: str) -> bool:
    return bool(re.match(r"^(?:infos?|informations?)\s+r[ée]gions?\s+\S", message.strip(), flags=re.IGNORECASE))


# Marseille, Lyon et Paris n'ont pas de code INSEE "commune" pour les mutations DVF :
# les ventes sont enregistrées par arrondissement municipal. Sans ça, une recherche
# sur le code commune global (13055, 69123, 75056) ne remonte aucune transaction.
PLM_ARRONDISSEMENT_CODES = {
    "13055": [f"132{i:02d}" for i in range(1, 17)],   # Marseille : 13201-13216
    "69123": [f"693{i:02d}" for i in range(81, 90)],  # Lyon : 69381-69389
    "75056": [f"751{i:02d}" for i in range(1, 21)],   # Paris : 75101-75120
}

# Fichiers "DVF géolocalisées" officiels Etalab/DGFiP, un CSV par commune,
# générés par https://github.com/datagouv/dvf et publiés sur data.gouv.fr.
# Remplace l'ancienne micro-API api.cquest.org/dvf (tombée en panne, 502 permanent).
GEO_DVF_YEAR = "2025"
GEO_DVF_BASE_URL = f"https://files.data.gouv.fr/geo-dvf/latest/csv/{GEO_DVF_YEAR}/communes"


def _departement_code(code_commune):
    """Code département à partir d'un code commune INSEE (gère Corse 2A/2B et DOM 97x)."""
    return code_commune[:3] if code_commune.startswith("97") else code_commune[:2]


DVF_LOCAL_TYPES = ("Appartement", "Maison")


async def fetch_dvf_transactions(client, code_commune):
    """Ventes réelles récentes (appartements et maisons) pour une commune, via le fichier CSV
    officiel "DVF géolocalisées" (Etalab/DGFiP), un fichier par commune sur files.data.gouv.fr/geo-dvf."""
    dept = _departement_code(code_commune)
    url = f"{GEO_DVF_BASE_URL}/{dept}/{code_commune}.csv"
    response = await client.get(url, timeout=30)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    reader = csv.DictReader(io.StringIO(response.text))
    return [
        row
        for row in reader
        if row.get("nature_mutation") == "Vente" and row.get("type_local") in DVF_LOCAL_TYPES
    ]


async def fetch_average_price_per_m2(client, insee_code):
    """Prix médian réel au m² (appartements + maisons) calculé à partir des transactions DVF
    officielles. Retourne None s'il n'y a pas assez de données vérifiées pour donner un chiffre honnête."""
    if not insee_code:
        return None

    codes = PLM_ARRONDISSEMENT_CODES.get(insee_code, [insee_code])
    tasks = [fetch_dvf_transactions(client, code) for code in codes]
    batches = await asyncio.gather(*tasks, return_exceptions=True)

    prices_per_m2 = []
    for batch in batches:
        if isinstance(batch, Exception):
            continue
        for transaction in batch:
            valeur = transaction.get("valeur_fonciere")
            surface = transaction.get("surface_reelle_bati")
            if not valeur or not surface:
                continue
            try:
                valeur_f = float(valeur)
                surface_f = float(surface)
            except (TypeError, ValueError):
                continue
            # Écarte les erreurs de saisie manifestes : valeur totale aberrante, surface ridicule.
            if not (10_000 <= valeur_f <= 20_000_000) or surface_f <= 9:
                continue
            try:
                price_m2 = valeur_f / surface_f
            except ZeroDivisionError:
                continue
            if 500 <= price_m2 <= 20000:
                prices_per_m2.append(price_m2)

    if len(prices_per_m2) < 5:
        return None

    return {
        "median": round(statistics.median(prices_per_m2)),
        "sample_size": len(prices_per_m2),
    }


def is_city_result_informative(result: dict) -> bool:
    """N'est mis en cache que si les champs clés contiennent de vraies données, pas des placeholders.
    L'historique n'est pas exigé : beaucoup de petites communes n'ont pas de page Wikipédia,
    ça ne doit pas empêcher de mettre en cache une fiche par ailleurs correcte (et donc bloquer
    ensuite "Voir les détails", qui a besoin d'une fiche de base déjà en cache)."""
    placeholder_markers = ("indisponible", "non précisée")
    for field in ("population", "area", "division"):
        value = result.get(field) or ""
        if not value or any(marker in value for marker in placeholder_markers):
            return False
    return True


async def get_city_info(query: str, force_refresh: bool = False) -> dict:
    """force_refresh=True ignore le cache SQLite existant (quelle que soit sa qualité) et
    relance une récupération complète, dont le résultat écrase l'entrée en cache."""
    normalized = query.strip().lower()
    if not force_refresh:
        try:
            async with async_session() as session:
                cached = await session.get(CityInfoCache, normalized)
                if cached:
                    cached_data = json.loads(cached.payload)
                    profile = next((value for key, value in CITY_PROFILES.items() if key in normalized), {})
                    merged_data = {**profile, **cached_data}
                    # Une entrée en cache non informative (ancien bug, placeholders) est traitée
                    # comme absente : on retombe plus bas pour la re-récupérer proprement.
                    if is_city_result_informative(merged_data):
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

    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=HTTP_HEADERS) as client:
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
        landmarks_task = fetch_nearby_landmarks(client, place.get("name", query), place.get("latitude"), place.get("longitude"))
        tasks = [country_task, history_task, landmarks_task]
        commune_task = fetch_french_commune_data(client, place.get("name", city_query)) if country_code == "FR" else None
        if commune_task is not None:
            tasks.append(commune_task)
        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        country_data, history, landmarks = gathered[0], gathered[1], gathered[2]
        commune_data = gathered[3] if commune_task is not None else {}
        if isinstance(country_data, Exception):
            logger.warning("fetch_country_data(%s) a échoué : %r", country_code, country_data)
            country_data = {}
        if isinstance(history, Exception):
            logger.warning("fetch_history(%s) a échoué : %r", place.get("name", query), history)
            history = "Aucun résumé historique disponible pour cette ville."
        if isinstance(landmarks, Exception):
            logger.warning("fetch_nearby_landmarks(%s) a échoué : %r", place.get("name", query), landmarks)
            landmarks = []
        if isinstance(commune_data, Exception):
            logger.warning("fetch_french_commune_data(%s) a échoué : %r", place.get("name", city_query), commune_data)
            commune_data = {}

    # Le prix au m² (DVF) et le budget de vie ne sont plus récupérés ici : ce sont des
    # "détails" coûteux (jusqu'à 16 requêtes DVF pour Marseille/Lyon/Paris) chargés à la
    # demande via get_city_details_status()/fetch_city_details() quand l'utilisateur clique
    # sur "Voir les détails" dans l'UI.

    country_name = country_data.get("translations", {}).get("fra", {}).get("common") or place.get("country", "Pays non précisé")
    city_population = commune_data.get("population") or place.get("population")
    country_population = country_data.get("population")
    # geo.api.gouv.fr renvoie "surface" en hectares, pas en km² : sans la conversion, toutes
    # les superficies de communes françaises étaient affichées 100x trop grandes.
    commune_surface_km2 = commune_data.get("surface")
    if commune_surface_km2:
        commune_surface_km2 = commune_surface_km2 / 100
    area = commune_surface_km2 or country_data.get("area")
    official_name = country_data.get("name", {}).get("official", country_name)
    region = country_data.get("region", "")
    subregion = country_data.get("subregion", "")
    capital = ", ".join(country_data.get("capital", [])) or "non précisée"
    languages = ", ".join(country_data.get("languages", {}).values()) or "non précisées"
    places_to_visit = ", ".join(landmarks) + "." if landmarks else "Aucun lieu notable identifié à proximité."

    departement = commune_data.get("departement") or {}
    commune_region = commune_data.get("region") or {}
    postal_codes = commune_data.get("codesPostaux") or []
    if departement.get("nom") or commune_region.get("nom"):
        division_parts = []
        if departement.get("nom"):
            division_parts.append(f"Département : {departement['nom']} ({departement.get('code', '')})")
        if commune_region.get("nom"):
            division_parts.append(f"Région : {commune_region['nom']}")
        if postal_codes:
            division_parts.append("Codes postaux : " + ", ".join(postal_codes))
        division = ". ".join(division_parts) + "."
    else:
        division = place.get("admin1", "Division administrative non précisée")

    result = {
        "city": place.get("name", query.title()),
        "country": country_name,
        "country_code": country_code,
        "insee_code": commune_data.get("code"),
        "population": format_population(city_population),
        "area": format_area(area),
        "division": division,
        "country_division": f"{official_name} est situé en {region}, sous-région {subregion or 'non précisée'}. Capitale : {capital}.",
        "economy": f"Pays de {country_name} en {region.lower() or 'développement'}, avec une population nationale d'environ {country_population:,} habitants et une économie décrite par les indicateurs nationaux.".replace(",", " ") if country_population else "Indicateurs économiques nationaux indisponibles.",
        "ethnicity": f"Les données ethniques ne sont pas comparables de façon homogène. Les langues officiellement recensées sont : {languages}.",
        "places_to_visit": places_to_visit,
        "strengths": [f"capitale ou centre régional de {country_name}", f"intégration dans la région {region or 'locale'}", "patrimoine et services urbains"],
        "weaknesses": ["les indicateurs locaux détaillés peuvent varier selon la source", "coût de la vie et logement à vérifier localement"],
        "history": history,
        "position": f"Coordonnées approximatives : {place.get('latitude', 'indisponible')}, {place.get('longitude', 'indisponible')}. Région : {region or 'non précisée'}.",
        "living_level": format_niveau_de_vie(departement) if country_code == "FR" else "Niveau de vie local à comparer avec les revenus, le logement et les services du pays.",
        "housing_price": "Prix au m² non disponible (cliquer sur « Voir les détails » pour le récupérer).",
        "comfortable_budget": format_comfortable_budget(departement) if country_code == "FR" else "Budget de vie confortable non disponible (aucune source vérifiée connectée pour cette donnée).",
    }
    if is_city_result_informative(result):
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


async def delete_city_info(query: str) -> bool:
    """Supprime définitivement l'entrée en cache SQLite d'une ville. Retourne True si une
    ligne a bien été supprimée, False si elle n'existait pas."""
    normalized = query.strip().lower()
    try:
        async with async_session() as session:
            cached = await session.get(CityInfoCache, normalized)
            if not cached:
                return False
            await session.delete(cached)
            await session.commit()
            return True
    except OperationalError:
        await init_db()
        return False


def _has_price_data(data: dict) -> bool:
    """True si le prix au m² en cache est une vraie donnée, pas le placeholder par défaut."""
    housing_price = data.get("housing_price") or ""
    return bool(housing_price) and "non disponible" not in housing_price


async def get_city_details_status(query: str) -> dict:
    """Lecture pure du cache, sans aucun appel réseau : dit si les "détails" (prix au m²,
    budget de vie) existent déjà, pour que l'UI puisse proposer une modale de confirmation
    avant de relancer les API coûteuses."""
    normalized = query.strip().lower()
    try:
        async with async_session() as session:
            cached = await session.get(CityInfoCache, normalized)
    except OperationalError:
        await init_db()
        cached = None

    if not cached:
        return {"has_cached_details": False, "data": None}

    data = json.loads(cached.payload)
    return {
        "has_cached_details": _has_price_data(data),
        "data": {
            "housing_price": data.get("housing_price"),
            "comfortable_budget": data.get("comfortable_budget"),
        },
    }


async def fetch_city_details(query: str) -> dict:
    """Récupère (ou re-récupère) les "détails" coûteux d'une ville et écrase l'entrée SQLite
    avec le résultat. S'il n'y a pas encore de fiche de base en cache (ex: petite commune sans
    page Wikipédia, jamais auto-cachée par get_city_info), va d'abord la chercher au lieu
    d'échouer — seule une ville introuvable (LookupError de get_city_info) reste une erreur."""
    normalized = query.strip().lower()
    async with async_session() as session:
        cached = await session.get(CityInfoCache, normalized)
    cached_data = json.loads(cached.payload) if cached else await get_city_info(query)

    country_code = cached_data.get("country_code")
    insee_code = cached_data.get("insee_code")

    housing_price = cached_data.get("housing_price")
    if country_code == "FR":
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=HTTP_HEADERS) as dvf_client:
                price_stats = await fetch_average_price_per_m2(dvf_client, insee_code)
        except (httpx.HTTPError, TypeError, ValueError) as error:
            logger.warning("fetch_average_price_per_m2(%s) a échoué : %r", insee_code, error)
            price_stats = None
        if price_stats:
            housing_price = (
                f"environ {price_stats['median']:,} €/m² "
                f"(médiane sur {price_stats['sample_size']} ventes d'appartements récentes, source DVF/DGFiP)."
            ).replace(",", " ")
        else:
            housing_price = "Prix au m² non disponible (données DVF insuffisantes pour cette ville)."
    else:
        housing_price = "Prix au m² non disponible (aucune source vérifiée connectée pour cette donnée)."

    # Budget de vie confortable : pas encore de source branchée (voir avec Sarah pour la clé INSEE).
    comfortable_budget = cached_data.get("comfortable_budget") or "Budget de vie confortable non disponible (aucune source vérifiée connectée pour cette donnée)."

    updated_data = {**cached_data, "housing_price": housing_price, "comfortable_budget": comfortable_budget}
    await save_city_info(normalized, updated_data)

    return {
        "has_cached_details": False,
        "data": {"housing_price": housing_price, "comfortable_budget": comfortable_budget},
    }


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


def is_city_refresh_request(message: str) -> bool:
    """Demande explicite de forcer une nouvelle récupération (bypass du cache)."""
    normalized = message.lower().strip()
    return normalized.startswith((
        "maj infos ", "maj info ",
        "actualise infos ", "actualise info ", "actualiser infos ",
        "rafraichis infos ", "rafraîchis infos ",
        "force infos ", "force info ",
        "mets à jour infos ", "met à jour infos ",
    ))