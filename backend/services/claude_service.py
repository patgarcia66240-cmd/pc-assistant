"""Claude API service"""
from config import settings

class ClaudeService:
    def __init__(self):
        self.client = None
        if settings.CLAUDE_API_KEY:
            try:
                from anthropic import AsyncAnthropic
                self.client = AsyncAnthropic(
                    api_key=settings.CLAUDE_API_KEY,
                    base_url=settings.CLAUDE_BASE_URL,
                )
            except ImportError:
                pass
    
    async def chat(self, message: str) -> str:
        """Send message to Claude"""
        if self.client is None:
            raise RuntimeError("Claude API is not configured")

        response = await self.client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            system=f"You are {settings.ARIA_NAME}, an AI assistant. Respond in {settings.ARIA_LANGUAGE}.",
            messages=[{"role": "user", "content": message}]
        )
        
        return response.content[0].text

claude_service = ClaudeService()
