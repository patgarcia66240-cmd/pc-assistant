import asyncio
from types import SimpleNamespace

from services.claude_service import claude_service
from services import claude_service as service_module
from plugins.config import router as config_router


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, response_payload, requests):
        self.response_payload = response_payload
        self.requests = requests

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def post(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return FakeResponse(self.response_payload)


def test_openai_provider_uses_chat_completions(monkeypatch):
    requests = []
    monkeypatch.setattr(service_module.settings, "AI_PROVIDER", "openai")
    monkeypatch.setattr(service_module.settings, "OPENAI_API_KEY", "openai-test")
    monkeypatch.setattr(service_module.settings, "OPENAI_MODEL", "gpt-test")
    monkeypatch.setattr(
        service_module.httpx,
        "AsyncClient",
        lambda timeout: FakeClient(
            {"choices": [{"message": {"content": "Réponse OpenAI"}}]},
            requests,
        ),
    )

    result = asyncio.run(
        claude_service.generate("Bonjour", system="Réponds en français", max_tokens=100)
    )

    assert result == "Réponse OpenAI"
    assert requests[0][0] == "https://api.openai.com/v1/chat/completions"
    assert requests[0][1]["headers"]["Authorization"] == "Bearer openai-test"
    assert requests[0][1]["json"]["model"] == "gpt-test"


def test_qwen_provider_uses_openai_compatible_endpoint(monkeypatch):
    requests = []
    monkeypatch.setattr(service_module.settings, "AI_PROVIDER", "qwen")
    monkeypatch.setattr(service_module.settings, "QWEN_API_KEY", "qwen-test")
    monkeypatch.setattr(service_module.settings, "QWEN_MODEL", "qwen-test-model")
    monkeypatch.setattr(
        service_module.httpx,
        "AsyncClient",
        lambda timeout: FakeClient(
            {"choices": [{"message": {"content": "Réponse Qwen"}}]},
            requests,
        ),
    )

    result = asyncio.run(
        claude_service.generate("Bonjour", system="Réponds en français", max_tokens=100)
    )

    assert result == "Réponse Qwen"
    assert requests[0][0].endswith("/compatible-mode/v1/chat/completions")
    assert requests[0][1]["json"]["model"] == "qwen-test-model"


def test_gemini_provider_uses_generate_content(monkeypatch):
    requests = []
    monkeypatch.setattr(service_module.settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(service_module.settings, "GEMINI_API_KEY", "gemini-test")
    monkeypatch.setattr(service_module.settings, "GEMINI_MODEL", "gemini-test-model")
    monkeypatch.setattr(
        service_module.httpx,
        "AsyncClient",
        lambda timeout: FakeClient(
            {"candidates": [{"content": {"parts": [{"text": "Réponse Gemini"}]}}]},
            requests,
        ),
    )

    result = asyncio.run(
        claude_service.generate("Bonjour", system="Réponds en français", max_tokens=100)
    )

    assert result == "Réponse Gemini"
    assert "/models/gemini-test-model:generateContent?key=gemini-test" in requests[0][0]
    assert requests[0][1]["json"]["system_instruction"]["parts"][0]["text"] == "Réponds en français"


def test_anthropic_provider_keeps_existing_client(monkeypatch):
    class FakeMessages:
        async def create(self, **kwargs):
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="Réponse Anthropic")]
            )

    monkeypatch.setattr(service_module.settings, "AI_PROVIDER", "anthropic")
    monkeypatch.setattr(service_module.settings, "CLAUDE_MODEL", "claude-test")
    monkeypatch.setattr(claude_service, "client", SimpleNamespace(messages=FakeMessages()))

    result = asyncio.run(
        claude_service.generate("Bonjour", system="Réponds en français", max_tokens=100)
    )

    assert result == "Réponse Anthropic"


def test_provider_key_is_saved_but_never_returned(monkeypatch):
    writes = []

    async def fake_geocode(city, country):
        return {"name": city, "latitude": 45.0, "longitude": 4.0}

    monkeypatch.setattr(config_router, "_geocode_location", fake_geocode)
    monkeypatch.setattr(
        config_router,
        "write_env_value",
        lambda key, value: writes.append((key, value)),
    )
    monkeypatch.setattr(config_router.settings, "QWEN_API_KEY", "")
    monkeypatch.setattr(config_router.settings, "QWEN_MODEL", "qwen-plus")
    monkeypatch.setattr(config_router.settings, "AI_PROVIDER", "anthropic")

    result = asyncio.run(
        config_router.update_app_preferences(
            config_router.AppPreferences(
                country="France",
                city="Lyon",
                ai_provider="qwen",
                ai_model="qwen-max",
                ai_api_key="secret-qwen-test",
            )
        )
    )

    assert ("QWEN_API_KEY", "secret-qwen-test") in writes
    assert result["preferences"]["ai_api_key"] == ""
    assert "secret-qwen-test" not in str(result)
