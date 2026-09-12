"""Routes for local Piper speech synthesis."""
import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from services import piper_tts_service


logger = logging.getLogger(__name__)
router = APIRouter()


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    speed: float = Field(default=0.92, ge=0.5, le=2)


def _unavailable_error() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="Piper n'est pas installé ou ses fichiers de modèle sont absents",
    )


@router.get("/status")
async def piper_status():
    return piper_tts_service.status()


@router.post("/warmup")
async def piper_warmup():
    if not piper_tts_service.status()["available"]:
        raise _unavailable_error()
    try:
        await run_in_threadpool(piper_tts_service.warm_up)
    except (ImportError, FileNotFoundError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (OSError, RuntimeError, ValueError) as error:
        logger.exception("Le préchargement de Piper a échoué")
        raise HTTPException(status_code=500, detail="Le préchargement de Piper a échoué") from error
    return {"ready": True}


@router.post("/synthesize")
async def piper_synthesize(payload: SpeechRequest):
    if not piper_tts_service.status()["available"]:
        raise _unavailable_error()
    try:
        audio = await run_in_threadpool(
            piper_tts_service.synthesize,
            payload.text,
            payload.speed,
        )
    except (ImportError, FileNotFoundError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (OSError, RuntimeError, ValueError) as error:
        logger.exception("La synthèse Piper a échoué")
        raise HTTPException(status_code=500, detail="La synthèse Piper a échoué") from error
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )
