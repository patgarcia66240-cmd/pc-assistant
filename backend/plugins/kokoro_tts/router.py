"""Routes for local Kokoro speech synthesis."""
from contextlib import asynccontextmanager
import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from services import kokoro_tts_service


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app):
    current_status = kokoro_tts_service.status()
    if current_status["available"]:
        try:
            await run_in_threadpool(kokoro_tts_service.warm_up)
            logger.info(
                "Kokoro préchargé avec %s",
                kokoro_tts_service.status()["provider"],
            )
        except (ImportError, FileNotFoundError, OSError, RuntimeError, ValueError):
            logger.exception("Le préchargement de Kokoro au démarrage a échoué")
    yield


router = APIRouter(lifespan=lifespan)


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    speed: float = Field(default=0.92, ge=0.5, le=2)


@router.get("/status")
async def kokoro_status():
    return kokoro_tts_service.status()


@router.post("/warmup")
async def kokoro_warmup():
    if not kokoro_tts_service.status()["available"]:
        raise HTTPException(
            status_code=503,
            detail="Kokoro n'est pas installé ou ses fichiers de modèle sont absents",
        )
    try:
        await run_in_threadpool(kokoro_tts_service.warm_up)
    except (ImportError, FileNotFoundError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (OSError, RuntimeError, ValueError) as error:
        logger.exception("Le préchargement de Kokoro a échoué")
        raise HTTPException(status_code=500, detail="Le préchargement de Kokoro a échoué") from error
    return {"ready": True}


@router.post("/synthesize")
async def kokoro_synthesize(payload: SpeechRequest):
    if not kokoro_tts_service.status()["available"]:
        raise HTTPException(
            status_code=503,
            detail="Kokoro n'est pas installé ou ses fichiers de modèle sont absents",
        )
    try:
        audio = await run_in_threadpool(
            kokoro_tts_service.synthesize,
            payload.text,
            payload.speed,
        )
    except (ImportError, FileNotFoundError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (OSError, RuntimeError, ValueError) as error:
        logger.exception("La synthèse Kokoro a échoué")
        raise HTTPException(status_code=500, detail="La synthèse Kokoro a échoué") from error
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )
