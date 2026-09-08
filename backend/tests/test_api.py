"""API endpoint tests"""
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

def test_aria_config_round_trip():
    response = client.put(
        "/api/config/aria",
        json={"name": "Test ARIA", "avatar": "X", "language": "en"},
    )
    assert response.status_code == 200
    assert client.get("/api/config/aria").json()["name"] == "Test ARIA"

def test_upload_is_scoped_to_files_root(monkeypatch, tmp_path):
    monkeypatch.setattr(FileService, "root", tmp_path)
    response = client.post(
        "/api/files/upload",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 200
    assert (tmp_path / "note.txt").read_bytes() == b"hello"
