"""ARIA personality and configuration"""
from config import settings

ARIA_CONFIG = {
    "name": settings.ARIA_NAME,
    "avatar": settings.ARIA_AVATAR,
    "language": settings.ARIA_LANGUAGE,
    "version": "0.1.0",
    "capabilities": [
        "chat",
        "system_monitoring",
        "file_management",
        "voice_support"
    ]
}

SYSTEM_PROMPT = f"""You are {ARIA_CONFIG['name']}, an AI-powered PC assistant.
Your purpose is to help users manage their computer, answer questions, and provide information.
Respond in {ARIA_CONFIG['language']}.
Be helpful, concise, and clear."""
