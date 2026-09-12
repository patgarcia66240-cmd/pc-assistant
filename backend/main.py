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
from plugin_loader import load_plugins, get_lifecycle_hooks

# Chat reste le seul routeur "métier" core : c'est lui qui appelle plugin_loader.get_chat_handlers()
# pour le routage par intention (voir routes/chat.py). Tout le reste (saints, calendar,
# city_details, kings, system, files, config) est passé en plugin le 11/09/2026 — voir
# backend/plugins/*. "plugins" est le routeur de gestion des plugins eux-mêmes (liste,
# activer/désactiver), forcément core lui aussi.
from routes import chat
from routes import plugins as plugins_route

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting PC Assistant Backend")
    await init_db()
    # Hooks de cycle de vie déclarés par des plugins (manifest "lifecycle": true, voir
    # plugin_loader.get_lifecycle_hooks()) — ex. plugins/messaging/lifecycle.py, qui lance
    # whatsapp-bridge/ et telegram_bot.py avec le backend. Récupérés une seule fois pour que
    # les MÊMES objets hook servent au shutdown ci-dessous (un hook garde son état en mémoire
    # entre les deux, ex. un subprocess.Popen). Un hook qui échoue est loggé, jamais fatal :
    # une erreur dans un plugin ne doit pas empêcher le reste du backend de démarrer.
    lifecycle_hooks = get_lifecycle_hooks()
    for hook in lifecycle_hooks:
        if hook["on_startup"] is None:
            continue
        try:
            await hook["on_startup"]()
        except Exception:
            logger.exception("Plugin '%s' : échec de on_startup", hook["id"])
    yield
    # Shutdown
    logger.info("Shutting down PC Assistant Backend")
    for hook in lifecycle_hooks:
        if hook["on_shutdown"] is None:
            continue
        try:
            await hook["on_shutdown"]()
        except Exception:
            logger.exception("Plugin '%s' : échec de on_shutdown", hook["id"])

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

# Include core routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(plugins_route.router, prefix="/api/plugins", tags=["plugins"])

# Découvre et monte les plugins activés (backend/plugins/*) — un plugin désactivé via
# POST /api/plugins/{id}/disable reste sur disque mais n'est pas monté tant que le backend
# n'a pas redémarré (voir plugin_loader.py).
load_plugins(app)

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
        # reload_includes (ajouté le 12/09/2026) : limite la surveillance aux fichiers .py.
        # Sans ça, uvicorn redémarre aussi sur toute écriture non-.py dans backend/ — déjà vu une
        # fois avec les logs whatsapp-bridge/ (voir plugins/messaging/lifecycle.py, LOG_DIR).
        # Coupable cette fois : backend/pc_assistant.db, réécrit à CHAQUE message traité (donc à
        # chaque message WhatsApp reçu ET chaque réponse d'ARIA) -> reload -> le hook on_shutdown
        # tue whatsapp-bridge/ -> on_startup le relance -> boucle de (re)connexion WhatsApp sans
        # fin (codes 408/428/515 dans run-logs/whatsapp-bridge.log), jamais stable assez longtemps
        # pour tenir une conversation.
        reload_includes=["*.py"],
    )
