"""
PC Assistant Backend - FastAPI Application
ARIA: AI-powered cross-platform PC management system
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging
from db import init_db
from config import settings

# Import routers
from routes import chat, system, files, config, saints, city_details, calendar

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
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])

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
    # Respecte API_HOST/API_PORT (config.py, défaut 127.0.0.1) au lieu de forcer 0.0.0.0 : sinon
    # l'API écoute sur toutes les interfaces réseau (pas juste en local), alors que /api/files et
    # /api/system n'ont aucune authentification — n'importe qui sur le même réseau pourrait y
    # accéder. Mets CORS_ORIGINS/API_HOST dans backend/.env si tu as vraiment besoin d'un accès LAN.
    #
    # reload=True (ajouté le 10/09/2026) : redémarre automatiquement ce serveur dès qu'un fichier
    # .py de backend/ change, au lieu de servir indéfiniment l'ancien code tant que tu ne fais pas
    # Ctrl+C puis relance à la main. Uniquement utilisé ici (démarrage dev via `python main.py` /
    # start-dev.sh) — la prod (start-production.sh) lance gunicorn directement, sans passer par ce
    # bloc, donc ce changement n'a aucun effet en prod. reload=True impose de passer l'appli comme
    # chaîne d'import ("main:app") plutôt que l'objet `app` directement (vérifié le 10/09/2026 sur
    # la doc uvicorn) ; reload_dirs limite la surveillance au dossier backend/ (pas tout le repo,
    # pas node_modules/venv) quel que soit le dossier depuis lequel le script est lancé.
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        reload_dirs=[str(Path(__file__).resolve().parent)],
    )
