"""Service IA multi-fournisseurs pour ARIA."""
import json
from collections.abc import AsyncIterator, Awaitable, Callable

import httpx

from config import settings


PROVIDER_LABELS = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "gemini": "Google Gemini",
    "qwen": "Qwen",
}


class ClaudeService:
    """Façade historique conservée pour les imports existants, désormais multi-fournisseurs."""

    def __init__(self):
        self.client = None
        self.refresh_anthropic_client()

    def refresh_anthropic_client(self) -> None:
        self.client = None
        if not settings.CLAUDE_API_KEY:
            return
        try:
            from anthropic import AsyncAnthropic

            self.client = AsyncAnthropic(
                api_key=settings.CLAUDE_API_KEY,
                base_url=settings.CLAUDE_BASE_URL,
            )
        except ImportError:
            pass

    def provider(self) -> str:
        return settings.AI_PROVIDER

    def model(self) -> str:
        return {
            "anthropic": settings.CLAUDE_MODEL,
            "openai": settings.OPENAI_MODEL,
            "gemini": settings.GEMINI_MODEL,
            "qwen": settings.QWEN_MODEL,
        }[self.provider()]

    def api_key(self) -> str:
        return {
            "anthropic": settings.CLAUDE_API_KEY,
            "openai": settings.OPENAI_API_KEY,
            "gemini": settings.GEMINI_API_KEY,
            "qwen": settings.QWEN_API_KEY,
        }[self.provider()]

    def is_configured(self) -> bool:
        if self.provider() == "anthropic":
            return self.client is not None
        return bool(self.api_key())

    async def chat(
        self,
        message: str,
        on_text: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        return await self.generate(
            message,
            system=(
                f"Tu es {settings.ARIA_NAME}, une assistante IA. "
                "Réponds toujours en français, même si le message reçu est dans une autre langue."
            ),
            max_tokens=1024,
            on_text=on_text,
        )

    async def generate(
        self,
        message: str,
        *,
        system: str,
        max_tokens: int,
        on_text: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        if not self.is_configured():
            raise RuntimeError(f"{PROVIDER_LABELS[self.provider()]} n'est pas configuré")
        if self.provider() == "anthropic":
            return await self._generate_anthropic(message, system, max_tokens, on_text)
        if self.provider() in {"openai", "qwen"}:
            return await self._generate_openai_compatible(message, system, max_tokens, on_text)
        return await self._generate_gemini(message, system, max_tokens, on_text)

    async def _generate_anthropic(
        self,
        message: str,
        system: str,
        max_tokens: int,
        on_text: Callable[[str], Awaitable[None]] | None,
    ) -> str:
        request = {
            "model": self.model(),
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": message}],
        }
        if on_text is not None:
            chunks = []
            async with self.client.messages.stream(**request) as stream:
                async for text in stream.text_stream:
                    chunks.append(text)
                    await on_text(text)
            return "".join(chunks)

        response = await self.client.messages.create(**request)
        return "".join(
            block.text
            for block in response.content
            if getattr(block, "type", "text") == "text"
        )

    async def _generate_openai_compatible(
        self,
        message: str,
        system: str,
        max_tokens: int,
        on_text: Callable[[str], Awaitable[None]] | None,
    ) -> str:
        provider = self.provider()
        base_url = (
            settings.OPENAI_BASE_URL
            if provider == "openai"
            else settings.QWEN_BASE_URL
        ).rstrip("/")
        request = {
            "model": self.model(),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
            "max_tokens": max_tokens,
            "stream": on_text is not None,
        }
        headers = {"Authorization": f"Bearer {self.api_key()}"}
        async with httpx.AsyncClient(timeout=120) as client:
            if on_text is None:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=request,
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]

            chunks = []
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers=headers,
                json=request,
            ) as response:
                response.raise_for_status()
                async for payload in self._sse_payloads(response.aiter_lines()):
                    if payload == "[DONE]":
                        break
                    text = json.loads(payload)["choices"][0].get("delta", {}).get("content")
                    if text:
                        chunks.append(text)
                        await on_text(text)
            return "".join(chunks)

    async def _generate_gemini(
        self,
        message: str,
        system: str,
        max_tokens: int,
        on_text: Callable[[str], Awaitable[None]] | None,
    ) -> str:
        action = "streamGenerateContent?alt=sse" if on_text is not None else "generateContent"
        url = (
            f"{settings.GEMINI_BASE_URL.rstrip('/')}/models/{self.model()}:{action}"
            f"{'&' if '?' in action else '?'}key={self.api_key()}"
        )
        request = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": message}]}],
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        async with httpx.AsyncClient(timeout=120) as client:
            if on_text is None:
                response = await client.post(url, json=request)
                response.raise_for_status()
                return self._gemini_text(response.json())

            chunks = []
            async with client.stream("POST", url, json=request) as response:
                response.raise_for_status()
                async for payload in self._sse_payloads(response.aiter_lines()):
                    text = self._gemini_text(json.loads(payload))
                    if text:
                        chunks.append(text)
                        await on_text(text)
            return "".join(chunks)

    @staticmethod
    async def _sse_payloads(lines: AsyncIterator[str]) -> AsyncIterator[str]:
        async for line in lines:
            if line.startswith("data:"):
                yield line[5:].strip()

    @staticmethod
    def _gemini_text(payload: dict) -> str:
        parts = payload["candidates"][0]["content"]["parts"]
        return "".join(part.get("text", "") for part in parts)


claude_service = ClaudeService()
