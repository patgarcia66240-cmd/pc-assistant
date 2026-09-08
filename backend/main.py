"""
PC Assistant Backend - FastAPI Application
ARIA: AI-powered cross-platform PC management system
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging
from db import init_db
from config import settings

# Import routers
from routes import chat, system, files, config, saints, city_details

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting PC Assistant Backend")
    await init_db()
    yield
    # Shutdown
    logger.info("Shutting down PC Assistant Backend")

# Create FastAPI app
app = FastAPI(
    title="PC Assistant API",
    description="ARIA - AI-powered PC management system",
    version="0.1.0",
    lifespan=lifespan
)

# Add middlewares
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(system.router, prefix="/api/system", tags=["system"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(saints.router, prefix="/api/saints", tags=["saints"])
app.include_router(city_details.router, prefix="/api/city-details", tags=["city-details"])

@app.get("/")
async def root():
    return {
        "name": "PC Assistant API",
        "version": "0.1.0",
        "status": "running",
        "ai": "ARIA"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
