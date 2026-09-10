"""Réponses financières basées sur des API gratuites.

Toutes les catégories ci-dessous se déclenchent avec le préfixe « bourse » OU « cours » (les deux
mots sont interchangeables, demande explicite de l'utilisatrice — voir _mentions_bourse) : bourse
forex, bourse cac40, bourse etf, bourse actions, bourse infos, bourse matières premières (ou
« cours forex », « cours cac40», etc.). « infos » reste réservé aux fiches ville/département/
région (city_info_service), donc un message comme « infos action Apple » ne doit pas passer par
ici — il faut dire « bourse action Apple » (ou « cours action Apple »).

Trois sources distinctes :
- Forex : Frankfurter (api.frankfurter.dev), gratuit, sans clé, sans limite — taux de change
  quotidiens publiés par la Banque Centrale Européenne (pas du temps réel).
- Actions, ETF, et tendances des marchés (via des ETF de référence) : Twelve Data
  (api.twelvedata.com), gratuit avec une clé API personnelle (800 requêtes/jour), couvre en
  priorité les actions et ETF américains sur le plan gratuit.
- CAC 40 : EODHD (eodhd.com), gratuit avec une clé API personnelle. Le plan gratuit (20
  requêtes/jour) ne donne accès qu'aux données de fin de journée (EOD), pas au temps réel — même
  logique que le forex via Frankfurter. Symbole vérifié directement via le compte EODHD de
  l'utilisatrice : "FCHI" sur l'exchange "INDX" (voir CAC40_SYMBOL). Une valeur EOD ne change
  qu'une fois par jour, donc la réponse est mise en cache un jour civil pour ménager le quota
  (voir _fetch_eodhd_eod / _eodhd_eod_cache, partagé avec les métaux).

- Métaux (or, argent, platine, palladium, cuivre, aluminium, plomb, nickel, zinc) : Metal
  Sentinel via RapidAPI (metal-sentinel.p.rapidapi.com), clé API personnelle (plan gratuit
  RapidAPI, sans carte bancaire). Deux fournisseurs essayés avant et abandonnés pour cette
  catégorie (voir historique) : Twelve Data (404 confirmés sur /quote ET /price en conditions
  réelles — plan gratuit qui ne couvre pas ces instruments) puis EODHD (tickers XAUUSD.FOREX
  etc., 404 constaté en pratique même pour les métaux précieux pourtant vérifiés existants côté
  EODHD — plan gratuit EODHD qui ne sert probablement pas les données FOREX EOD).

  Endpoints Metal Sentinel : le panneau "Endpoints" de RapidAPI les affiche sous /api/... (ex.
  /api/metal-quote, /api/gold-price, /api/silver-price), mais c'est TROMPEUR — confirmé par DEUX
  404 réels en conditions réelles (logs backend) avec le corps {"message":"Endpoint '/api/...'
  does not exist"}, pour /api/silver-price ET /api/metal-quote. Les vrais chemins n'ont PAS le
  préfixe /api/ : /metal-quote (générique, précieux + base, paramètre metal=<code>), /gold-price
  et /silver-price (endpoints dédiés, un par métal — il n'existe PAS d'endpoint dédié pour les 7
  métaux de base, qui passent donc par /metal-quote). Réponses confirmées 200 OK en conditions
  réelles pour /gold-price?currency=USD et /silver-price?currency=USD (cette dernière renvoie en
  plus "change"/"changePercentage" — donc une variation EST disponible, contrairement à ce qu'on
  pensait au départ ; /metal-quote pour les autres métaux n'a pas encore été confirmé avec le bon
  chemin — le corps de la réponse est loggé côté backend sur toute erreur (>=400) pour
  diagnostiquer sans repasser par l'UI RapidAPI si besoin). Les 10 codes métaux (AU/AG/PT/PD/RH/
  CU/NI/AL/PB/ZN) viennent de l'endpoint "allowed-metals" (chemin exact non vérifié avec notre
  code, l'utilisatrice a testé via l'UI RapidAPI sans coller l'URL utilisée — même remarque pour
  "allowed-currencies", qui confirme USD et EUR supportés) ; seuls les 9 demandés par
  l'utilisatrice sont câblés (voir METALS) — le rhodium (RH) pourrait être ajouté pareil si
  besoin.

Les autres matières premières (pétrole, agricole...) ne sont pas couvertes pour l'instant. La vue
"tendances des marchés" (bourse infos) ne reflète, elle, que les marchés américains via
SPY/DIA/QQQ (le CAC 40 et les métaux ont chacun leur propre catégorie).

Important : is_market_overview_request N'EST PAS un attrape-tout sur « bourse » seul (ça a causé
un bug réel : un mot non reconnu, ex. « bourse cuivre » avant l'ajout du cuivre, tombait
silencieusement sur les ETF américains). Elle exige « infos »/« tendances »/« comment va » —
c'est le mot dédié à cette catégorie, comme les autres. Le vrai attrape-tout final, is_bourse_
request + get_unknown_bourse_answer (voir chat.py), répond clairement « catégorie non reconnue »
plutôt que de deviner une catégorie ou de laisser tomber sur l'IA générale (qui pourrait inventer
un chiffre).
"""
import logging
import re
from datetime import date, timedelta

import httpx

from config import settings
from services.local_service import normalize_text, _strip_filler_suffix

logger = logging.getLogger(__name__)

FRANKFURTER_URL = "https://api.frankfurter.dev/v2/rates"
TWELVE_DATA_URL = "https://api.twelvedata.com"
EODHD_URL = "https://eodhd.com/api"
# Confirmé via l'API exchange-symbol-list de l'utilisatrice : Code="FCHI", Exchange="INDX".
CAC40_SYMBOL = "FCHI.INDX"
METAL_SENTINEL_URL = "https://metal-sentinel.p.rapidapi.com"
METAL_SENTINEL_HOST = "metal-sentinel.p.rapidapi.com"

# Devises affichées par défaut pour "bourse forex" (aucune devise précisée dans la demande).
DEFAULT_FOREX_QUOTES = ("USD", "GBP", "CHF", "JPY")

# ETF utilisés comme proxy des grands indices américains pour "bourse infos" : Twelve Data ne
# donne pas accès aux indices bruts sur le plan gratuit, mais les ETF qui les répliquent, eux,
# sont accessibles. Cette vue ne couvre donc que les marchés américains ; le CAC 40 est couvert
# séparément via EODHD (voir get_cac40_answer).
MARKET_OVERVIEW_PROXIES = (
    ("S&P 500", "SPY"),
    ("Dow Jones", "DIA"),
    ("Nasdaq 100", "QQQ"),
)

# Cache mémoire générique {ticker: {"date": ..., "rows": ...}} pour les requêtes EODHD EOD (CAC
# 40 uniquement désormais — les métaux sont passés à Metal Sentinel) : le plan gratuit EODHD est
# limité à 20 requêtes/jour, et une clôture ne change qu'une fois par jour de toute façon
# (données EOD, pas temps réel) -> on ne rappelle l'API qu'une fois par jour civil et par ticker
# (voir _fetch_eodhd_eod).
_eodhd_eod_cache: dict = {}

# Métaux ("bourse or", "bourse argent", "bourse cuivre", ...) via Metal Sentinel (RapidAPI) :
# codes vérifiés via /api/allowed-metals (endpoint officiel Metal Sentinel qui liste les codes
# supportés) ET testés en direct par l'utilisatrice pour AU et AG (voir historique).
METALS = {
    "or": ("Or", "AU"),
    "argent": ("Argent", "AG"),
    "platine": ("Platine", "PT"),
    "palladium": ("Palladium", "PD"),
    "cuivre": ("Cuivre", "CU"),
    "aluminium": ("Aluminium", "AL"),
    "plomb": ("Plomb", "PB"),
    "nickel": ("Nickel", "NI"),
    "zinc": ("Zinc", "ZN"),
}

# Endpoints DÉDIÉS Metal Sentinel pour l'or et l'argent. IMPORTANT : ils ne sont PAS sous /api/
# malgré ce qu'affiche le tableau "Endpoints" du panneau RapidAPI (qui liste "/api/silver-price"
# — trompeur, corrigé en pratique) : un vrai appel à /api/silver-price renvoie 404 avec le corps
# {"message":"Endpoint '/api/silver-price' does not exist"} (log backend réel), alors que
# /silver-price (sans /api) avait déjà répondu 200 OK lors du test direct de l'utilisatrice sur
# RapidAPI. Il n'existe pas d'endpoint dédié pour les 7 autres métaux : ceux-là passent par le
# endpoint générique /metal-quote?symbol=<code> (sans /api non plus — même correction, après un
# 404 réel "{'message':\"Endpoint '/api/metal-quote' does not exist\"}" ; paramètre "symbol"
# confirmé fonctionnel en conditions réelles, ex. nickel).
METAL_DEDICATED_ENDPOINTS = {
    "AU": "/gold-price",
    "AG": "/silver-price",
}


def _mentions_bourse(normalized: str) -> bool:
    # « bourse » et « cours » sont interchangeables comme mot déclencheur (demande explicite de
    # l'utilisatrice) : « cours or » ou « bourse or » donnent le même résultat. Risque connu et
    # accepté : « cours » est un mot français courant hors contexte boursier (« cours de piano »,
    # « en cours »...) — un message qui le contient sans mot-clé boursier reconnu à côté tombera
    # sur le message « catégorie non reconnue » (voir get_unknown_bourse_answer) plutôt que sur
    # l'IA générale ou une autre catégorie. A resserrer si ça pose problème en pratique.
    return bool(re.search(r"\b(?:bourse|cours)\b", normalized))


def _detect_metal(normalized: str):
    for keyword, info in METALS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", normalized):
            return info
    return None


def is_forex_request(message: str) -> bool:
    normalized = normalize_text(message)
    if not _mentions_bourse(normalized):
        return False
    if re.search(r"\bforex\b", normalized):
        return True
    return any(term in normalized for term in ("devises", "taux de change"))


def is_cac40_request(message: str) -> bool:
    normalized = normalize_text(message)
    if not _mentions_bourse(normalized):
        return False
    return bool(re.search(r"\bcac\s?-?\s?40\b", normalized)) or "cac quarante" in normalized


def is_commodities_request(message: str) -> bool:
    normalized = normalize_text(message)
    if not _mentions_bourse(normalized):
        return False
    if _detect_metal(normalized):
        return True
    return any(term in normalized for term in (
        "matiere premiere",
        "matieres premieres",
        "matieres premiere",
        "matiere premieres",
        "commodities",
    ))


def is_stock_request(message: str) -> bool:
    normalized = normalize_text(message)
    return _mentions_bourse(normalized) and bool(re.search(r"\bactions?\b", normalized))


def is_etf_request(message: str) -> bool:
    normalized = normalize_text(message)
    return _mentions_bourse(normalized) and bool(re.search(r"\betf\b", normalized))


def is_market_overview_request(message: str) -> bool:
    # NE PAS transformer en attrape-tout sur « bourse » seul : un mot non reconnu (ex. « bourse
    # cuivre » avant l'ajout du cuivre) tomberait alors silencieusement sur les ETF américains
    # (SPY/DIA/QQQ), ce qui est trompeur (constaté en pratique). On exige donc une intention
    # explicite de "vue d'ensemble" — comme convenu : « bourse infos » est le mot dédié à cette
    # catégorie, au même titre que forex/cac40/etf/actions/matières premières ont les leurs.
    normalized = normalize_text(message)
    if not _mentions_bourse(normalized):
        return False
    if normalized.strip() in ("bourse", "cours"):
        return True
    return any(term in normalized for term in ("infos", "informations", "tendance", "tendances", "comment va"))


def is_bourse_request(message: str) -> bool:
    return _mentions_bourse(normalize_text(message))


def _extract_query_after(normalized: str, keyword_pattern: str) -> str | None:
    match = re.search(rf"{keyword_pattern}\s+(?:de\s+|d\s+|sur\s+|pour\s+|l\s+|la\s+)?(.+)$", normalized)
    if not match:
        return None
    query = match.group(1).strip(" ?.!\t")
    query = _strip_filler_suffix(query)
    return query or None


def extract_stock_query(message: str) -> str | None:
    return _extract_query_after(normalize_text(message), r"\bactions?\b")


def extract_etf_query(message: str) -> str | None:
    return _extract_query_after(normalize_text(message), r"\betf\b")


def _to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def get_forex_answer() -> dict:
    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.get(
            FRANKFURTER_URL,
            params={"base": "EUR", "quotes": ",".join(DEFAULT_FOREX_QUOTES)},
        )
        response.raise_for_status()
        payload = response.json()

    if not isinstance(payload, list) or not payload:
        return {"text": "Impossible de récupérer les cours des devises pour le moment.", "rates": [], "date": None}

    rates = [{"pair": f"EUR/{item['quote']}", "rate": item["rate"]} for item in payload if "quote" in item and "rate" in item]
    date = payload[0].get("date")
    summary = ", ".join(f"{item['pair']} : {item['rate']}" for item in rates)
    date_suffix = f" ({date})" if date else ""
    return {
        "text": f"Cours des devises, Banque Centrale Européenne{date_suffix} : {summary}." if rates else "Impossible de récupérer les cours des devises pour le moment.",
        "rates": rates,
        "date": date,
    }


def _twelve_data_error(payload) -> str | None:
    """Twelve Data renvoie un objet {'status': 'error', 'code': ..., 'message': ...} plutôt
    qu'un code HTTP d'erreur pour une clé invalide, un symbole non couvert par le plan
    gratuit, un quota dépassé, etc."""
    if isinstance(payload, dict) and payload.get("status") == "error":
        return payload.get("message") or "Cette donnée n'est pas disponible avec la clé API actuelle."
    return None


async def _resolve_symbol(client: httpx.AsyncClient, query: str) -> dict | None:
    response = await client.get(
        f"{TWELVE_DATA_URL}/symbol_search",
        params={"symbol": query, "outputsize": 5, "apikey": settings.TWELVE_DATA_API_KEY},
    )
    response.raise_for_status()
    payload = response.json()
    if _twelve_data_error(payload):
        return None
    candidates = payload.get("data") if isinstance(payload, dict) else None
    if not candidates:
        return None
    return candidates[0]


async def _fetch_quote(client: httpx.AsyncClient, symbol: str, mic_code: str | None = None) -> dict | None:
    # mic_code désambiguïse les symboles qui existent sur plusieurs places (ex. CW8 coté à
    # Paris) : sans lui, /quote répond 404 pour un symbole pourtant valide trouvé par
    # symbol_search (constaté en pratique sur "bourse etf CW8", corrigé ici).
    params = {"symbol": symbol, "apikey": settings.TWELVE_DATA_API_KEY}
    if mic_code:
        params["mic_code"] = mic_code
    response = await client.get(f"{TWELVE_DATA_URL}/quote", params=params)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def _quote_direction(change) -> str:
    value = _to_float(change)
    if value is None:
        return "stable"
    if value > 0:
        return "en hausse"
    if value < 0:
        return "en baisse"
    return "stable"


def _format_quote_text(name: str, symbol: str, quote: dict) -> str:
    price = quote.get("close")
    currency = quote.get("currency") or ""
    percent = quote.get("percent_change")
    direction = _quote_direction(quote.get("change"))
    percent_text = f" ({percent} %)" if percent not in (None, "") else ""
    return f"{name} ({symbol}) : {price} {currency}, {direction}{percent_text} sur la séance.".strip()


async def get_market_quote_answer(query: str | None, kind: str) -> dict:
    """kind : 'stock' ou 'etf' — Twelve Data utilise le même point d'accès pour les deux, seul
    le texte diffère."""
    label = "l'action" if kind == "stock" else "l'ETF"
    example = "bourse action Apple" if kind == "stock" else "bourse etf CW8"

    if not settings.TWELVE_DATA_API_KEY:
        return {
            "text": f"La clé API Twelve Data n'est pas configurée (variable TWELVE_DATA_API_KEY dans le fichier .env).",
            "quote": None,
        }
    if not query:
        return {"text": f"Précisez {label}, par exemple : « {example} ».", "quote": None}

    async with httpx.AsyncClient(timeout=8) as client:
        candidate = await _resolve_symbol(client, query)
        if not candidate:
            return {"text": f"Je ne trouve pas {label} « {query} ».", "quote": None}

        symbol = candidate.get("symbol")
        name = candidate.get("instrument_name") or symbol
        if not symbol:
            return {"text": f"Je ne trouve pas {label} « {query} ».", "quote": None}

        quote = await _fetch_quote(client, symbol, candidate.get("mic_code"))
        if quote is None:
            return {"text": f"Je ne trouve pas de cours pour {name} ({symbol}).", "quote": None}
        error_message = _twelve_data_error(quote)
        if error_message:
            return {"text": f"{name} : {error_message}", "quote": None}

        display_name = quote.get("name") or name
        return {
            "text": _format_quote_text(display_name, symbol, quote),
            "quote": {
                "name": display_name,
                "symbol": symbol,
                "exchange": quote.get("exchange"),
                "currency": quote.get("currency"),
                "price": quote.get("close"),
                "previous_close": quote.get("previous_close"),
                "change": quote.get("change"),
                "percent_change": quote.get("percent_change"),
                "kind": kind,
            },
        }


async def get_market_overview_answer() -> dict:
    if not settings.TWELVE_DATA_API_KEY:
        return {
            "text": "La clé API Twelve Data n'est pas configurée (variable TWELVE_DATA_API_KEY dans le fichier .env).",
            "indices": [],
        }

    indices = []
    async with httpx.AsyncClient(timeout=8) as client:
        for label, symbol in MARKET_OVERVIEW_PROXIES:
            try:
                quote = await _fetch_quote(client, symbol)
            except httpx.HTTPError:
                continue
            if quote is None or _twelve_data_error(quote):
                continue
            indices.append({
                "label": label,
                "symbol": symbol,
                "price": quote.get("close"),
                "change": quote.get("change"),
                "percent_change": quote.get("percent_change"),
                "currency": quote.get("currency"),
            })

    if not indices:
        return {"text": "Impossible de récupérer les tendances des marchés pour le moment.", "indices": []}

    summary = ", ".join(f"{item['label']} {item['percent_change']} %" for item in indices)
    return {
        "text": f"Tendances des marchés américains (via ETF de référence) : {summary}.",
        "indices": indices,
    }


async def _fetch_eodhd_eod(client: httpx.AsyncClient, ticker: str) -> list | None:
    """Renvoie les ~10 dernières séances EOD (triées par date croissante) pour `ticker`, ou None
    si le ticker est introuvable (404) ou si la réponse est vide/invalide. Met en cache un jour
    civil par ticker (voir _eodhd_eod_cache) : les données EOD ne changent qu'une fois par jour,
    et le plan gratuit EODHD est limité à 20 requêtes/jour."""
    today = date.today().isoformat()
    cached = _eodhd_eod_cache.get(ticker)
    if cached and cached["date"] == today:
        return cached["rows"]

    # Fenêtre de 10 jours pour être sûr d'avoir au moins 2 séances (week-ends, jours fériés).
    from_date = (date.today() - timedelta(days=10)).isoformat()
    response = await client.get(
        f"{EODHD_URL}/eod/{ticker}",
        params={"api_token": settings.EODHD_API_KEY, "fmt": "json", "period": "d", "from": from_date},
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or not payload:
        return None

    rows = sorted(payload, key=lambda row: row.get("date", ""))
    _eodhd_eod_cache[ticker] = {"date": today, "rows": rows}
    return rows


def _eod_change(rows: list) -> tuple:
    """A partir de rows triées (croissant), calcule (close, prev_close, change, percent_change,
    date_label) de la dernière séance vs la précédente."""
    latest = rows[-1]
    previous = rows[-2] if len(rows) >= 2 else None
    close = _to_float(latest.get("close"))
    prev_close = _to_float(previous.get("close")) if previous else None
    change = round(close - prev_close, 4) if (close is not None and prev_close is not None) else None
    percent_change = round(change / prev_close * 100, 2) if (change is not None and prev_close) else None
    return close, prev_close, change, percent_change, latest.get("date", "")


async def get_cac40_answer() -> dict:
    if not settings.EODHD_API_KEY:
        return {
            "text": "La clé API EODHD n'est pas configurée (variable EODHD_API_KEY dans le fichier .env).",
            "quote": None,
        }

    async with httpx.AsyncClient(timeout=8) as client:
        rows = await _fetch_eodhd_eod(client, CAC40_SYMBOL)

    if rows is None:
        return {"text": "Le CAC 40 n'est pas disponible via EODHD pour le moment (symbole introuvable).", "quote": None}

    close, prev_close, change, percent_change, date_label = _eod_change(rows)
    direction = _quote_direction(change)
    percent_text = f" ({percent_change} %)" if percent_change is not None else ""

    return {
        "text": (
            f"CAC 40 : {close} points, {direction}{percent_text} "
            f"(clôture du {date_label} — données EODHD de fin de journée, pas temps réel)."
        ),
        "quote": {
            "name": "CAC 40",
            "symbol": "FCHI",
            "exchange": "Euronext Paris",
            "currency": "points",
            "price": close,
            "previous_close": prev_close,
            "change": change,
            "percent_change": percent_change,
            "date": date_label,
            "kind": "cac40",
        },
    }


async def get_commodities_answer(message: str) -> dict:
    metal = _detect_metal(normalize_text(message))
    if not metal:
        return {
            "text": (
                "Précisez le métal : or, argent, platine, palladium, cuivre, aluminium, plomb, "
                "nickel ou zinc (ex. « bourse or »). Les autres matières premières ne sont pas "
                "encore disponibles."
            ),
            "quote": None,
        }
    label, code = metal

    if not settings.METAL_SENTINEL_API_KEY:
        return {
            "text": "La clé API Metal Sentinel n'est pas configurée (variable METAL_SENTINEL_API_KEY dans le fichier .env).",
            "quote": None,
        }

    # Or et argent : endpoint dédié, confirmé fiable. Les autres métaux n'ont pas d'endpoint
    # dédié chez Metal Sentinel -> on passe par le générique /metal-quote (voir docstring : aucun
    # endpoint Metal Sentinel n'est sous /api/, malgré ce qu'affichait le panneau RapidAPI —
    # confirmé par deux 404 réels "/api/metal-quote does not exist" en conditions réelles).
    path = METAL_DEDICATED_ENDPOINTS.get(code, "/metal-quote")
    params = {"currency": "USD"}
    if path == "/metal-quote":
        # Paramètre "symbol" (pas "metal") d'après la doc RapidAPI vue par l'utilisatrice —
        # NON encore vérifié par un test réel avec /metal-quote (le seul test réel de ce
        # endpoint utilisait "metal=" avec l'ancien préfixe /api, avant qu'on découvre que ce
        # préfixe était faux). A confirmer par un test en conditions réelles.
        params["symbol"] = code

    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.get(
            f"{METAL_SENTINEL_URL}{path}",
            params=params,
            headers={
                "x-rapidapi-host": METAL_SENTINEL_HOST,
                "x-rapidapi-key": settings.METAL_SENTINEL_API_KEY,
            },
        )
        if response.status_code in (401, 403):
            return {"text": "Clé API Metal Sentinel invalide ou abonnement RapidAPI manquant.", "quote": None}
        if response.status_code >= 400:
            # Corps de la réponse loggé (jamais montré tel quel à l'utilisatrice) pour pouvoir
            # diagnostiquer une erreur inattendue à partir des logs backend, sans repasser par
            # l'UI RapidAPI (cf. anomalie non résolue sur metal=AG&currency=USD).
            logger.warning(
                "Metal Sentinel %s pour %s (%s) via %s%s : %s",
                response.status_code, label, code, path, response.url.query.decode() if response.url.query else "",
                response.text[:500],
            )
            if response.status_code == 404:
                return {"text": f"Je ne trouve pas de cours pour {label} ({code}) chez Metal Sentinel.", "quote": None}
            return {"text": f"Erreur Metal Sentinel ({response.status_code}) pour {label} ({code}).", "quote": None}
        response.raise_for_status()
        payload = response.json()

    results = payload.get("results") if isinstance(payload, dict) else None
    if isinstance(results, dict):
        results = [results]
    if not results:
        return {"text": f"Je ne trouve pas de cours pour {label} ({code}) chez Metal Sentinel.", "quote": None}

    entry = results[0]
    price = _to_float(entry.get("mid"))
    if price is None:
        price = _to_float(entry.get("ask"))
    if price is None:
        price = _to_float(entry.get("bid"))
    if price is None:
        return {"text": f"Réponse inattendue de Metal Sentinel pour {label} — impossible d'en extraire un prix.", "quote": None}
    currency = entry.get("currency") or "USD"
    change = _to_float(entry.get("change"))
    percent_change = _to_float(entry.get("changePercentage"))

    # Metal Sentinel renvoie des flottants à ~15 décimales (ex. 7.599562241023323) : on arrondit
    # pour l'affichage, comme pour les autres catégories (CAC40, forex, actions...).
    price = round(price, 2)
    if change is not None:
        change = round(change, 2)
    if percent_change is not None:
        percent_change = round(percent_change, 2)

    if change is not None and percent_change is not None:
        direction = _quote_direction(change)
        text = f"{label} : {price} {currency}, {direction} ({percent_change} %) — cours Metal Sentinel."
    else:
        text = f"{label} : {price} {currency} (cours Metal Sentinel, rafraîchi en continu ; variation indisponible)."

    return {
        "text": text,
        "quote": {
            "name": label,
            "symbol": code,
            "exchange": "Metal Sentinel",
            "currency": currency,
            "price": price,
            "previous_close": None,
            "change": change,
            "percent_change": percent_change,
            "kind": "commodities",
        },
    }


def get_unknown_bourse_answer() -> dict:
    # Filet de sécurité final pour tout message « bourse ... » qu'aucune catégorie plus précise
    # n'a reconnu (ordre vérifié dans chat.py). Répondre clairement ici évite deux pièges validés
    # en pratique : (1) laisser tomber sur is_market_overview_request en attrape-tout silencieux
    # (donnait les ETF américains pour un mot non reconnu, ex. « bourse cuivre » avant son ajout —
    # trompeur) ; (2) laisser tomber sur l'IA générale, qui pourrait inventer un chiffre boursier.
    return {
        "text": (
            "Je n'ai pas reconnu cette demande boursière. Catégories disponibles (« bourse » et "
            "« cours » sont équivalents) : « bourse forex », « bourse cac40 », « bourse etf "
            "<nom> », « bourse action <nom> », « bourse or/argent/platine/palladium/cuivre/"
            "aluminium/plomb/nickel/zinc », ou « bourse infos » pour les tendances des marchés "
            "américains."
        ),
    }
