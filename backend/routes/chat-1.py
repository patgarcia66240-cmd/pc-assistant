"""Chat routes with Claude API integration"""
import re
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.claude_service import claude_service
from services.local_service import (
    get_ram_answer,
    get_g7_time_answer,
    get_time_answer,
    get_weather_answer,
    is_ram_request,
    is_world_time_request,
    is_time_request,
    is_weather_request,
)
from services.city_info_service import (
    get_city_info,
    is_city_info_request,
    is_city_refresh_request,
    is_departement_info_request,
    is_region_info_request,
    fetch_departement_info,
    fetch_region_info,
)
from services.market_service import (
    get_cac40_answer,
    get_commodities_answer,
    get_forex_answer,
    get_market_overview_answer,
    get_market_quote_answer,
    get_unknown_bourse_answer,
    is_bourse_request,
    is_cac40_request,
    is_commodities_request,
    is_forex_request,
    is_market_overview_request,
    is_stock_request,
    is_etf_request,
    extract_stock_query,
    extract_etf_query,
)
from services.kings_service import (
    get_king_answer,
    is_king_request,
)

router = APIRouter()


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

class ChatMessage(BaseModel):
    message: str
    context: dict = {}

@router.post("/")
async def chat(message: ChatMessage):
    """Send message to ARIA"""
    if not message.message.strip():
        raise HTTPException(status_code=422, detail="Message cannot be empty")

    if is_ram_request(message.message):
        return {"response": get_ram_answer(), "context": message.context, "status": "success", "source": "local", "source_type": "system"}
    if is_city_refresh_request(message.message):
        query = re.sub(
            r"^(?:maj|force|actualiser?|rafra[iî]chis|mets?\s+à\s+jour)\s+infos?(?:\s+sur)?\s+",
            "",
            message.message.strip(),
            flags=re.IGNORECASE,
        )
        try:
            city_info = await get_city_info(query, force_refresh=True)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except (httpx.HTTPError, IndexError, KeyError) as error:
            raise HTTPException(status_code=502, detail="City information service unavailable") from error
        return {"response": f"Informations actualisées sur {city_info['city']}", "data": city_info, "context": message.context, "status": "success", "source": "local", "source_type": "city_info"}
    if is_departement_info_request(message.message):
        query = re.sub(r"^(?:infos?|informations?)\s+d[ée]partements?\s+", "", message.message.strip(), flags=re.IGNORECASE)
        try:
            dept_info = await fetch_departement_info(query)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except (httpx.HTTPError, IndexError, KeyError) as error:
            raise HTTPException(status_code=502, detail="City information service unavailable") from error
        return {"response": f"Informations sur le département {dept_info['nom']}", "data": dept_info, "context": message.context, "status": "success", "source": "local", "source_type": "departement_info"}
    if is_region_info_request(message.message):
        query = re.sub(r"^(?:infos?|informations?)\s+r[ée]gions?\s+", "", message.message.strip(), flags=re.IGNORECASE)
        try:
            region_info = await fetch_region_info(query)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except (httpx.HTTPError, IndexError, KeyError) as error:
            raise HTTPException(status_code=502, detail="City information service unavailable") from error
        return {"response": f"Informations sur la région {region_info['nom']}", "data": region_info, "context": message.context, "status": "success", "source": "local", "source_type": "region_info"}
    if is_city_info_request(message.message):
        query = re.sub(r"^(?:infos?|informations?)(?:\s+sur)?\s+", "", message.message.strip(), flags=re.IGNORECASE)
        try:
            city_info = await get_city_info(query)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except (httpx.HTTPError, IndexError, KeyError) as error:
            raise HTTPException(status_code=502, detail="City information service unavailable") from error
        return {"response": f"Informations sur {city_info['city']}", "data": city_info, "context": message.context, "status": "success", "source": "local", "source_type": "city_info"}
    if is_world_time_request(message.message):
        return {"response": "Heure des capitales du G7", "data": get_g7_time_answer(), "context": message.context, "status": "success", "source": "local", "source_type": "world_time"}
    if is_time_request(message.message):
        try:
            response = await get_time_answer(message.message, message.context.get("location"))
        except (httpx.HTTPError, IndexError, KeyError, ValueError, TypeError) as error:
            raise HTTPException(status_code=502, detail="Time service unavailable") from error
        time_data = parse_time_response(response)
        location_label = "Heure France"
        if response.startswith("Heure à "):
            location_name = response.removeprefix("Heure à ").split(" :", 1)[0]
            country_name = location_name.rsplit(",", 1)[-1].strip() if "," in location_name else location_name
            location_label = f"Heure {country_name}"
        return {"response": response, "time_data": time_data, "time_label": location_label, "context": message.context, "status": "success", "source": "local", "source_type": "time"}
    if is_weather_request(message.message):
        try:
            response = await get_weather_answer(message.message, message.context.get("location"))
        except Exception as error:
            raise HTTPException(status_code=502, detail="Weather service unavailable") from error
        return {
            "response": response["text"],
            "context": message.context,
            "status": "success",
            "source": "local",
            "source_type": "weather",
            "weather_type": response["weather_type"],
        }
    if is_forex_request(message.message):
        try:
            response = await get_forex_answer()
        except Exception as error:
            raise HTTPException(status_code=502, detail="Forex service unavailable") from error
        return {
            "response": response["text"],
            "data": {"rates": response["rates"], "date": response["date"]},
            "context": message.context,
            "status": "success",
            "source": "local",
            "source_type": "forex",
        }
    if is_cac40_request(message.message):
        try:
            response = await get_cac40_answer()
        except Exception as error:
            raise HTTPException(status_code=502, detail="CAC40 service unavailable") from error
        return {
            "response": response["text"],
            "data": response.get("quote"),
            "context": message.context,
            "status": "success",
            "source": "local",
            "source_type": "cac40",
        }
    if is_etf_request(message.message):
        try:
            response = await get_market_quote_answer(extract_etf_query(message.message), kind="etf")
        except Exception as error:
            raise HTTPException(status_code=502, detail="Market data service unavailable") from error
        return {
            "response": response["text"],
            "data": response["quote"],
            "context": message.context,
            "status": "success",
            "source": "local",
            "source_type": "etf",
        }
    if is_stock_request(message.message):
        try:
            response = await get_market_quote_answer(extract_stock_query(message.message), kind="stock")
        except Exception as error:
            raise HTTPException(status_code=502, detail="Market data service unavailable") from error
        return {
            "response": response["text"],
            "data": response["quote"],
            "context": message.context,
            "status": "success",
            "source": "local",
            "source_type": "stock",
        }
    if is_commodities_request(message.message):
        try:
            response = await get_commodities_answer(message.message)
        except Exception as error:
            raise HTTPException(status_code=502, detail="Commodities service unavailable") from error
        return {
            "response": response["text"],
            "data": response.get("quote"),
            "context": message.context,
            "status": "success",
            "source": "local",
            "source_type": "commodities",
        }
    if is_market_overview_request(message.message):
        # « bourse infos »/« tendances »/« comment va » : vérifié après les catégories plus
        # spécifiques (forex/cac40/etf/actions/matières premières), mais ce N'EST PAS un
        # attrape-tout sur « bourse » seul (voir is_bourse_request plus bas et le commentaire dans
        # market_service.py) — un mot non reconnu ne doit pas tomber ici silencieusement.
        try:
            response = await get_market_overview_answer()
        except Exception as error:
            raise HTTPException(status_code=502, detail="Market overview service unavailable") from error
        return {
            "response": response["text"],
            "data": response["indices"],
            "context": message.context,
            "status": "success",
            "source": "local",
            "source_type": "market_overview",
        }
    if is_bourse_request(message.message):
        # Vrai attrape-tout final : "bourse" est présent mais aucune sous-catégorie n'a été
        # reconnue. On le dit clairement plutôt que de laisser tomber sur l'IA générale, qui
        # pourrait inventer un chiffre boursier.
        response = get_unknown_bourse_answer()
        return {
            "response": response["text"],
            "context": message.context,
            "status": "success",
            "source": "local",
            "source_type": "bourse_unknown",
        }
    if is_king_request(message.message):
        # Fiches des rois de France servies depuis SQLite (data/kings.db), jamais par l'IA
        # générative (demande explicite : ne pas appeler l'IA pour rien pour ces faits). Une
        # seule fonction gère requête vide / roi non trouvé / plusieurs rois ambigus / roi trouvé
        # (voir kings_service.get_king_answer) — pas besoin d'un attrape-tout séparé comme pour
        # bourse/cours, il n'y a qu'une seule sous-catégorie ici.
        try:
            response = await get_king_answer(message.message)
        except Exception as error:
            raise HTTPException(status_code=502, detail="Kings database service unavailable") from error
        return {
            "response": response["text"],
            "data": response.get("king"),
            "context": message.context,
            "status": "success",
            "source": "local",
            "source_type": "king",
        }

    if claude_service.client is None:
        raise HTTPException(status_code=503, detail="Claude API is not configured")

    try:
        response = await claude_service.chat(message.message)
        return {
            "response": response,
            "context": message.context,
            "status": "success",
            "source": "ai",
        }
    except Exception as error:
        if getattr(error, "status_code", None) == 401:
            raise HTTPException(status_code=502, detail="Claude API key is invalid or expired") from error
        raise HTTPException(status_code=502, detail="Claude API request failed") from error

@router.get("/history")
async def get_history():
    """Get chat history"""
    return {"messages": []}
