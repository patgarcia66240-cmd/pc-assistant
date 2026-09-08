"""Configuration management"""
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./pc_assistant.db")
    ARIA_NAME: str = os.getenv("ARIA_NAME", "ARIA")
    ARIA_AVATAR: str = os.getenv("ARIA_AVATAR", "🤖")
    ARIA_LANGUAGE: str = os.getenv("ARIA_LANGUAGE", "fr")
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True

    class Config:
        env_file = ".env"

settings = Settings()
