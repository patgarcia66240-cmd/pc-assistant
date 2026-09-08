"""Claude API service"""
from anthropic import Anthropic
from config import settings

class ClaudeService:
    def __init__(self):
        self.client = Anthropic(api_key=settings.CLAUDE_API_KEY)
        self.conversation_history = []
    
    async def chat(self, message: str) -> str:
        """Send message to Claude"""
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=f"You are {settings.ARIA_NAME}, an AI assistant. Respond in {settings.ARIA_LANGUAGE}.",
            messages=self.conversation_history
        )
        
        assistant_message = response.content[0].text
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message

claude_service = ClaudeService()
