"""API endpoint tests"""
import json

import pytest
from fastapi.testclient import TestClient
from main import app
from services.file_service import FileService

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "PC Assistant API" in response.json()["name"]

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_chat_without_claude(monkeypatch):
    from services.claude_service import claude_service
    monkeypatch.setattr(claude_service, "client", None)
    response = client.post("/api/chat/", json={"message": "Hello"})
    assert response.status_code == 503

def test_chat_stream_emits_text_as_it_arrives(monkeypatch):
    from config import settings
    from services.claude_service import claude_service

    class FakeMessageStream:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            pass

        @property
        def text_stream(self):
            async def chunks():
                for text in ("Bonjour", " depuis", " ARIA."):
                    yield text

            return chunks()

    class FakeMessages:
        def stream(self, **kwargs):
            return FakeMessageStream()

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr(settings, "AI_PROVIDER", "anthropic")
    monkeypatch.setattr(claude_service, "client", FakeClient())

    with client.stream("POST", "/api/chat/stream", json={"message": "Présente-toi"}) as response:
        events = [json.loads(line) for line in response.iter_lines()]

    assert response.status_code == 200
    assert [event["text"] for event in events if event["type"] == "delta"] == [
        "Bonjour",
        " depuis",
        " ARIA.",
    ]
    assert events[-1]["type"] == "done"
    assert events[-1]["data"]["response"] == "Bonjour depuis ARIA."

def test_chat_ram_does_not_require_claude(monkeypatch):
    from services.claude_service import claude_service
    monkeypatch.setattr(claude_service, "client", None)
    response = client.post("/api/chat/", json={"message": "Quelle est la mémoire RAM de mon PC ?"})
    assert response.status_code == 200
    assert response.json()["source"] == "local"
    assert "RAM disponible" in response.json()["response"]

def test_chat_time_does_not_require_claude(monkeypatch):
    from services.claude_service import claude_service
    monkeypatch.setattr(claude_service, "client", None)
    response = client.post("/api/chat/", json={"message": "Quelle heure est-il ?"})
    assert response.status_code == 200
    assert response.json()["source"] == "local"
    assert response.json()["source_type"] == "time"
    assert "Heure en France" in response.json()["response"]
    assert "UTC" in response.json()["response"]
    assert "heure d'" in response.json()["response"]


def test_chat_opens_whatsapp_plugin_without_claude(monkeypatch):
    from services.claude_service import claude_service

    monkeypatch.setattr(claude_service, "client", None)
    response = client.post("/api/chat/", json={"message": "WhatsApp"})

    assert response.status_code == 200
    assert response.json()["source_type"] == "whatsapp_open"
    assert response.json()["data"]["navigate_to"] == "whatsapp"

def test_chat_give_time_does_not_require_claude(monkeypatch):
    from services.claude_service import claude_service
    monkeypatch.setattr(claude_service, "client", None)
    response = client.post("/api/chat/", json={"message": "donne l'heure"})
    assert response.status_code == 200
    assert response.json()["source"] == "local"

def test_chat_time_for_city_does_not_require_claude(monkeypatch):
    from services.claude_service import claude_service
    monkeypatch.setattr(claude_service, "client", None)
    response = client.post("/api/chat/", json={"message": "heure de Marseille"})
    assert response.status_code == 200
    assert response.json()["source"] == "local"
    assert response.json()["source_type"] == "time"

def test_time_city_name_is_extracted():
    import asyncio
    from services.local_service import get_time_answer
    response = asyncio.run(get_time_answer("heure Orange, US"))
    assert "Orange" in response
    assert "États-Unis" in response

def test_country_aliases():
    from services.local_service import country_code
    assert country_code("es") == "ES"
    assert country_code("Angleterre") == "GB"
    assert country_code("gb") == "GB"
    assert country_code("bg") == "BG"
    assert country_code("Belgique") == "BE"
    assert country_code("Allemagne") == "DE"
    assert country_code("Royaume-Uni") == "GB"

def test_world_time_g7_does_not_require_claude(monkeypatch):
    from services.claude_service import claude_service
    monkeypatch.setattr(claude_service, "client", None)
    response = client.post("/api/chat/", json={"message": "heure monde"})
    assert response.status_code == 200
    assert response.json()["source"] == "local"
    assert response.json()["source_type"] == "world_time"
    assert all(item in {entry["city"] for entry in response.json()["data"]} for item in (
        "Washington", "Ottawa", "Londres", "Paris", "Berlin", "Rome", "Tokyo"
    ))

def test_city_info_berlin_does_not_require_claude(monkeypatch):
    from services.claude_service import claude_service
    monkeypatch.setattr(claude_service, "client", None)
    response = client.post("/api/chat/", json={"message": "infos Berlin"})
    assert response.status_code == 200
    assert response.json()["source_type"] == "city_info"
    assert response.json()["data"]["country"] == "Allemagne"

def test_city_info_madrid_has_complete_local_profile(monkeypatch):
    from services.claude_service import claude_service
    monkeypatch.setattr(claude_service, "client", None)
    response = client.post("/api/chat/", json={"message": "infos Madrid"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["population"] != "Donnée détaillée à compléter"
    assert data["markets"] == "IBEX 35, indice principal de la Bourse espagnole de Madrid."
    assert data["housing_price"]
    assert data["comfortable_budget"]

def test_city_info_is_cached_in_sqlite():
    from sqlalchemy import select
    from db import async_session
    from models.conversation import CityInfoCache
    import asyncio

    async def read_cache():
        async with async_session() as session:
            return (await session.execute(select(CityInfoCache).where(CityInfoCache.query == "berlin"))).scalar_one_or_none()

    cached = asyncio.run(read_cache())
    assert cached is not None
    assert cached.city == "Berlin"

def test_city_info_compound_name_uses_hyphens():
    from services.city_info_service import geocoding_city_name
    assert geocoding_city_name("st martin de crau") == "st-martin-de-crau"

def test_european_capitals_catalogue():
    from services.city_info_service import EUROPEAN_CAPITALS
    assert len(EUROPEAN_CAPITALS) >= 40
    assert ("Paris", "FR") in EUROPEAN_CAPITALS
    assert ("Madrid", "ES") in EUROPEAN_CAPITALS
    assert ("Berlin", "DE") in EUROPEAN_CAPITALS

def test_chat_date_question_does_not_require_claude(monkeypatch):
    from services.claude_service import claude_service
    monkeypatch.setattr(claude_service, "client", None)
    response = client.post("/api/chat/", json={"message": "Quelle est la date ?"})
    assert response.status_code == 200
    assert response.json()["source"] == "local"

def test_extract_composed_city_name():
    from services.local_service import extract_city, geocoding_city_name
    assert extract_city("météo salon de provence") == "salon de provence"
    assert extract_city("météo de Saint-Étienne") == "saint-etienne"
    assert geocoding_city_name("salon de provence") == "salon-de-provence"
    assert geocoding_city_name("saint etienne") == "saint-etienne"

def test_weather_description():
    from services.local_service import weather_description
    assert weather_description(0) == "ciel dégagé"
    assert weather_description(63) == "pluie"

def test_weather_message_rounds_measurements(monkeypatch):
    import asyncio
    from services import local_service

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self.payload

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            pass

        async def get(self, url, **kwargs):
            if "reverse-geocode" in url:
                return FakeResponse({"city": "Paris"})
            return FakeResponse({
                "current": {
                    "temperature_2m": 18.6,
                    "weather_code": 0,
                    "wind_speed_10m": 12.4,
                }
            })

    monkeypatch.setattr(local_service.httpx, "AsyncClient", FakeAsyncClient)
    result = asyncio.run(local_service.get_weather_answer(
        "météo",
        {"latitude": 48.8566, "longitude": 2.3522},
    ))

    assert result["text"] == "Météo à Paris : ciel dégagé, 19 °C, vent 12 km/h."

def test_saint_of_day():
    from datetime import date
    from services.saint_service import get_saint_of_day
    saint = get_saint_of_day(date(2026, 9, 8))
    assert saint["name"] == "La Nativité de la Vierge Marie"
    assert saint["story"]
    assert saint["display_date"] == "mardi 8 septembre 2026"
    assert saint["observances"][0]["name"] == "Journée internationale de l'alphabétisation"

def test_system_info():
    response = client.get("/api/system/info")
    assert response.status_code == 200
    assert "cpu_percent" in response.json()
    assert "drives" in response.json()
    assert isinstance(response.json()["drives"], list)

def test_aria_config_round_trip(monkeypatch):
    from config import settings
    from plugins.config import router as config_router

    original = (settings.ARIA_NAME, settings.ARIA_AVATAR, settings.ARIA_LANGUAGE)
    monkeypatch.setattr(config_router, "write_env_value", lambda *_args, **_kwargs: None)
    try:
        response = client.put(
            "/api/config/aria",
            json={"name": "Test ARIA", "avatar": "X", "language": "fr"},
        )
        assert response.status_code == 200
        assert client.get("/api/config/aria").json() == {
            "name": "Test ARIA",
            "avatar": "X",
            "language": "fr",
        }
        rejected = client.put(
            "/api/config/aria",
            json={"name": "Test ARIA", "avatar": "X", "language": "en"},
        )
        assert rejected.status_code == 422
    finally:
        settings.ARIA_NAME, settings.ARIA_AVATAR, settings.ARIA_LANGUAGE = original

def test_app_preferences_round_trip(monkeypatch):
    from config import settings
    from plugins.config import router as config_router

    async def fake_geocode(city, country):
        assert city == "Lyon"
        assert country == "France"
        return {"name": "Lyon", "latitude": 45.764, "longitude": 4.8357}

    monkeypatch.setattr(config_router, "_geocode_location", fake_geocode)
    monkeypatch.setattr(config_router, "write_env_value", lambda key, value: None)
    monkeypatch.setattr(settings, "USER_COUNTRY", settings.USER_COUNTRY)
    monkeypatch.setattr(settings, "USER_CITY_LABEL", settings.USER_CITY_LABEL)
    monkeypatch.setattr(settings, "USER_LATITUDE", settings.USER_LATITUDE)
    monkeypatch.setattr(settings, "USER_LONGITUDE", settings.USER_LONGITUDE)
    monkeypatch.setattr(settings, "AI_PROVIDER", settings.AI_PROVIDER)
    monkeypatch.setattr(settings, "CLAUDE_MODEL", settings.CLAUDE_MODEL)

    response = client.put(
        "/api/config/preferences",
        json={
            "country": "France",
            "city": "Lyon",
            "ai_provider": "anthropic",
            "ai_model": "claude-test-model",
        },
    )

    assert response.status_code == 200
    preferences = client.get("/api/config/preferences").json()
    assert {
        key: preferences[key]
        for key in ("country", "city", "ai_provider", "ai_model")
    } == {
        "country": "France",
        "city": "Lyon",
        "ai_provider": "anthropic",
        "ai_model": "claude-test-model",
    }
    assert preferences["ai_api_key"] == ""
    assert "openai" in preferences["ai_providers"]
    assert "gemini" in preferences["ai_providers"]
    assert "qwen" in preferences["ai_providers"]

def test_upload_is_scoped_to_files_root(monkeypatch, tmp_path):
    monkeypatch.setattr(FileService, "root", tmp_path)
    response = client.post(
        "/api/files/upload",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 200
    assert (tmp_path / "note.txt").read_bytes() == b"hello"

def test_kokoro_status():
    response = client.get("/api/tts/status")
    assert response.status_code == 200
    assert {"available", "dependencies_installed", "model_installed", "voice", "provider"} <= response.json().keys()

def test_kokoro_warmup(monkeypatch):
    from services import kokoro_tts_service

    monkeypatch.setattr(
        kokoro_tts_service,
        "status",
        lambda: {
            "available": True,
            "dependencies_installed": True,
            "model_installed": True,
            "voice": "ff_siwis",
        },
    )
    warmed_up = []
    monkeypatch.setattr(kokoro_tts_service, "warm_up", lambda: warmed_up.append(True))

    response = client.post("/api/tts/warmup")

    assert response.status_code == 200
    assert response.json() == {"ready": True}
    assert warmed_up == [True]

def test_kokoro_is_preloaded_during_startup(monkeypatch):
    from services import kokoro_tts_service

    monkeypatch.setattr(
        kokoro_tts_service,
        "status",
        lambda: {"available": True, "provider": "CUDAExecutionProvider"},
    )
    warmed_up = []
    monkeypatch.setattr(kokoro_tts_service, "warm_up", lambda: warmed_up.append(True))

    with TestClient(app):
        pass

    assert warmed_up == [True]

def test_kokoro_synthesize_returns_wav(monkeypatch):
    from services import kokoro_tts_service

    monkeypatch.setattr(
        kokoro_tts_service,
        "status",
        lambda: {
            "available": True,
            "dependencies_installed": True,
            "model_installed": True,
            "voice": "ff_siwis",
        },
    )
    monkeypatch.setattr(kokoro_tts_service, "synthesize", lambda text, speed: b"RIFF-test-wave")

    response = client.post(
        "/api/tts/synthesize",
        json={"text": "Bonjour depuis ARIA.", "speed": 0.92},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == b"RIFF-test-wave"

def test_piper_status():
    response = client.get("/api/piper-tts/status")
    assert response.status_code == 200
    assert {"available", "dependencies_installed", "model_installed", "voice"} <= response.json().keys()

def test_piper_warmup(monkeypatch):
    from services import piper_tts_service

    monkeypatch.setattr(
        piper_tts_service,
        "status",
        lambda: {
            "available": True,
            "dependencies_installed": True,
            "model_installed": True,
            "voice": "fr_FR-siwis-medium",
        },
    )
    warmed_up = []
    monkeypatch.setattr(piper_tts_service, "warm_up", lambda: warmed_up.append(True))

    response = client.post("/api/piper-tts/warmup")

    assert response.status_code == 200
    assert response.json() == {"ready": True}
    assert warmed_up == [True]

def test_piper_synthesize_returns_wav(monkeypatch):
    from services import piper_tts_service

    monkeypatch.setattr(
        piper_tts_service,
        "status",
        lambda: {
            "available": True,
            "dependencies_installed": True,
            "model_installed": True,
            "voice": "fr_FR-siwis-medium",
        },
    )
    monkeypatch.setattr(piper_tts_service, "synthesize", lambda text, speed: b"RIFF-piper-wave")

    response = client.post(
        "/api/piper-tts/synthesize",
        json={"text": "Bonjour rapidement.", "speed": 1.0},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == b"RIFF-piper-wave"
