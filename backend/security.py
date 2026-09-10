"""Optional protection for sensitive local API routes."""
import secrets

from fastapi import Header, HTTPException

from config import settings


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Require X-API-Key when API_AUTH_TOKEN is configured.

    The default remains compatible with the local development setup. Setting
    API_AUTH_TOKEN enables protection for configuration and calendar mutations.
    """
    if settings.API_AUTH_TOKEN and not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    if settings.API_AUTH_TOKEN and not secrets.compare_digest(x_api_key, settings.API_AUTH_TOKEN):
        raise HTTPException(status_code=403, detail="Invalid API key")
