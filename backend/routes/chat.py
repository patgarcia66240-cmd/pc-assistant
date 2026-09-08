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
from services.city_info_service import get_city_info, is_city_info_request

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
    if is_city_info_request(message.message):
        query = re.sub(r"^(?:infos?|informations?)(?:\s+sur)?\s+", "", message.message.strip(), flags=re.IGNORECASE)
        try:
            city_info = await get_city_info(query)
        except (httpx.HTTPError, IndexError, KeyError) as error:
            raise HTTPException(status_code=502, detail="City information service unavailable") from error
        return {"response": f"Informations sur {city_info['city']}", "data": city_info, "context": message.context, "status": "success", "source": "local", "source_type": "city_info"}
    if is_world_time_request(message.message):
        return {"response": "Heure des capitales du G7", "data": get_g7_time_answer(), "context": message.context, "status": "success", "source": "local", "source_type": "world_time"}
    if is_time_request(message.message):
        response = await get_time_answer(message.message, message.context.get("location"))
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
