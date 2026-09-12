"""Handler de chat pour la bourse (forex, CAC 40, ETF, actions, matières premières, tendances) —
extrait de routes/chat.py le 12/09/2026 (voir ram/city_info/heure_meteo/calendar pour le reste du
même chantier). Sept cas regroupés dans l'ordre d'origine — l'ORDRE compte : les catégories
spécifiques (forex, cac40, etf, actions, matières premières, tendances) sont vérifiées avant le
vrai attrape-tout final (is_bourse_request), pour ne jamais laisser tomber une demande boursière
reconnue sur l'IA générative qui pourrait inventer un chiffre.

Erreurs : chaque cas gardait un message distinct dans chat.py ("Forex service unavailable",
"CAC40 service unavailable", "Market data service unavailable" pour etf/actions, "Commodities
service unavailable", "Market overview service unavailable") — préservé ici en les attrapant
explicitement plutôt que de laisser le mécanisme générique de plugin_loader appliquer un seul
chat_error_message à tous (voir manifest.json, "Bourse service unavailable" n'est qu'un filet de
secours). Le dernier cas (bourse_unknown) ne peut pas échouer (réponse statique)."""
import httpx
from fastapi import HTTPException

from services.market_service import (
    extract_etf_query,
    extract_stock_query,
    get_cac40_answer,
    get_commodities_answer,
    get_forex_answer,
    get_market_overview_answer,
    get_market_quote_answer,
    get_unknown_bourse_answer,
    is_bourse_request,
    is_cac40_request,
    is_commodities_request,
    is_etf_request,
    is_forex_request,
    is_market_overview_request,
    is_stock_request,
)

SERVICE_ERRORS = (httpx.HTTPError, LookupError, IndexError, KeyError, ValueError, TypeError)


def matches(message: str) -> bool:
    return (
        is_forex_request(message)
        or is_cac40_request(message)
        or is_etf_request(message)
        or is_stock_request(message)
        or is_commodities_request(message)
        or is_market_overview_request(message)
        or is_bourse_request(message)
    )


async def handle(message: str, context: dict) -> dict:
    if is_forex_request(message):
        try:
            response = await get_forex_answer()
        except SERVICE_ERRORS as error:
            raise HTTPException(status_code=502, detail="Forex service unavailable") from error
        return {
            "response": response["text"],
            "data": {"rates": response["rates"], "date": response["date"]},
            "source": "local",
            "source_type": "forex",
        }

    if is_cac40_request(message):
        try:
            response = await get_cac40_answer()
        except SERVICE_ERRORS as error:
            raise HTTPException(status_code=502, detail="CAC40 service unavailable") from error
        return {
            "response": response["text"],
            "data": response.get("quote"),
            "source": "local",
            "source_type": "cac40",
        }

    if is_etf_request(message):
        try:
            response = await get_market_quote_answer(extract_etf_query(message), kind="etf")
        except SERVICE_ERRORS as error:
            raise HTTPException(status_code=502, detail="Market data service unavailable") from error
        return {
            "response": response["text"],
            "data": response["quote"],
            "source": "local",
            "source_type": "etf",
        }

    if is_stock_request(message):
        try:
            response = await get_market_quote_answer(extract_stock_query(message), kind="stock")
        except SERVICE_ERRORS as error:
            raise HTTPException(status_code=502, detail="Market data service unavailable") from error
        return {
            "response": response["text"],
            "data": response["quote"],
            "source": "local",
            "source_type": "stock",
        }

    if is_commodities_request(message):
        try:
            response = await get_commodities_answer(message)
        except SERVICE_ERRORS as error:
            raise HTTPException(status_code=502, detail="Commodities service unavailable") from error
        return {
            "response": response["text"],
            "data": response.get("quote"),
            "source": "local",
            "source_type": "commodities",
        }

    if is_market_overview_request(message):
        # « bourse infos »/« tendances »/« comment va » : vérifié après les catégories plus
        # spécifiques ci-dessus, mais ce N'EST PAS un attrape-tout sur « bourse » seul (voir
        # is_bourse_request plus bas et le commentaire dans market_service.py).
        try:
            response = await get_market_overview_answer()
        except SERVICE_ERRORS as error:
            raise HTTPException(status_code=502, detail="Market overview service unavailable") from error
        return {
            "response": response["text"],
            "data": response["indices"],
            "source": "local",
            "source_type": "market_overview",
        }

    # is_bourse_request(message) — vrai attrape-tout final, dernier cas possible garanti par
    # matches() ci-dessus : "bourse" est présent mais aucune sous-catégorie n'a été reconnue. On
    # le dit clairement plutôt que de laisser tomber sur l'IA générale.
    response = get_unknown_bourse_answer()
    return {
        "response": response["text"],
        "source": "local",
        "source_type": "bourse_unknown",
    }
