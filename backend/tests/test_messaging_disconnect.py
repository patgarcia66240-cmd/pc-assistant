import asyncio

from plugins.messaging import router as messaging_router


class FakeResponse:
    def raise_for_status(self):
        return None


class FakeAsyncClient:
    def __init__(self, requests):
        self.requests = requests

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def post(self, url, headers):
        self.requests.append((url, headers))
        return FakeResponse()


def test_disconnect_whatsapp_calls_bridge_logout(monkeypatch):
    requests = []

    monkeypatch.setattr(messaging_router.settings, "WHATSAPP_BRIDGE_SECRET", "test-secret")
    monkeypatch.setattr(messaging_router.settings, "WHATSAPP_BRIDGE_URL", "http://127.0.0.1:3001")
    monkeypatch.setattr(
        messaging_router.httpx,
        "AsyncClient",
        lambda timeout: FakeAsyncClient(requests),
    )

    result = asyncio.run(messaging_router.disconnect_whatsapp())

    assert result["status"] == "disconnected"
    assert requests == [
        (
            "http://127.0.0.1:3001/logout",
            {"X-Bridge-Secret": "test-secret"},
        )
    ]


def test_disconnect_telegram_stops_bot_and_clears_local_config(monkeypatch):
    stopped = []
    writes = []

    monkeypatch.setattr(messaging_router.settings, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(messaging_router.settings, "TELEGRAM_ALLOWED_USER_IDS", "123")
    monkeypatch.setattr(
        messaging_router.lifecycle,
        "stop_telegram_bot",
        lambda: stopped.append(True) or True,
    )
    monkeypatch.setattr(
        messaging_router,
        "write_env_value",
        lambda key, value: writes.append((key, value)),
    )

    result = asyncio.run(messaging_router.disconnect_telegram())

    assert result["status"] == "disconnected"
    assert stopped == [True]
    assert writes == [
        ("TELEGRAM_BOT_TOKEN", ""),
        ("TELEGRAM_ALLOWED_USER_IDS", ""),
    ]
    assert messaging_router.settings.TELEGRAM_BOT_TOKEN == ""
    assert messaging_router.settings.TELEGRAM_ALLOWED_USER_IDS == ""
