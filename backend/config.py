"""Configuration management"""
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / ".env")

class Settings(BaseSettings):
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_BASE_URL: str = os.getenv("CLAUDE_BASE_URL", "https://api.anthropic.com")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./pc_assistant.db")
    FILES_ROOT: str = os.getenv("FILES_ROOT", os.path.expanduser("~"))
    ARIA_NAME: str = os.getenv("ARIA_NAME", "ARIA")
    ARIA_AVATAR: str = os.getenv("ARIA_AVATAR", "🤖")
    ARIA_LANGUAGE: str = os.getenv("ARIA_LANGUAGE", "fr")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    class Config:
        env_file = ".env"

settings = Settings()
