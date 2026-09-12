import asyncio
import base64
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import delete

from config import settings
from db import async_session
from main import app
from plugins.image_generation.models import GeneratedImage


def test_generate_image_stores_and_serves_png(monkeypatch):
    image_bytes = b"\x89PNG\r\n\x1a\nfake-image"
    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": [
                    {
                        "b64_json": base64.b64encode(image_bytes).decode("ascii"),
                        "revised_prompt": "Un robot ARIA bleu",
                    }
                ]
            }

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, **kwargs):
            captured["url"] = url
            captured["request"] = kwargs
            return FakeResponse()

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(settings, "OPENAI_IMAGE_MODEL", "gpt-image-2")
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)

    prompt = f"Robot ARIA {uuid4()}"
    image_id = None
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/images/generate",
                json={"prompt": prompt, "size": "1536x1024", "quality": "medium"},
            )
            assert response.status_code == 200
            payload = response.json()
            image_id = payload["id"]
            assert payload["revised_prompt"] == "Un robot ARIA bleu"
            assert captured["url"].endswith("/images/generations")
            assert captured["request"]["json"]["model"] == "gpt-image-2"
            assert captured["request"]["json"]["size"] == "1536x1024"
            assert captured["request"]["headers"]["Authorization"] == "Bearer test-openai-key"

            stored = client.get("/api/images")
            assert any(image["id"] == image_id for image in stored.json()["images"])

            image_response = client.get(f"/api/images/{image_id}")
            assert image_response.status_code == 200
            assert image_response.headers["content-type"] == "image/png"
            assert image_response.content == image_bytes
    finally:
        if image_id:
            async def cleanup():
                async with async_session() as session:
                    await session.execute(delete(GeneratedImage).where(GeneratedImage.id == image_id))
                    await session.commit()

            asyncio.run(cleanup())


def test_chat_handler_matches_and_extracts_prompt():
    from plugins.image_generation.chat_handler import extract_prompt, handle, matches

    msg1 = "génère une image d'un pirate à Paris s'il te plaît"
    assert matches(msg1)
    assert extract_prompt(msg1) == "Un pirate à Paris"

    msg2 = "peux-tu me créer un dessin de chat volant"
    assert matches(msg2)
    assert extract_prompt(msg2) == "Chat volant"

    msg3 = "Quelle heure est-il ?"
    assert not matches(msg3)

    result = asyncio.run(handle(msg1, {}))
    assert result["data"]["navigate_to"] == "image_generation"
    assert result["data"]["prompt"] == "Un pirate à Paris"
    assert result["data"]["auto_submit"] is True


def test_generate_image_requires_openai_key(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")

    with TestClient(app) as client:
        response = client.post(
            "/api/images/generate",
            json={"prompt": "Un paysage futuriste", "size": "1024x1024", "quality": "low"},
        )

    assert response.status_code == 503
    assert "clé API OpenAI" in response.json()["detail"]
