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

# Import routers
from routes import chat, system, files, config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting PC Assistant Backend")
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
    allow_origins=["*"],  # Configured for dev; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(system.router, prefix="/api/system", tags=["system"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(config.router, prefix="/api/config", tags=["config"])

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
