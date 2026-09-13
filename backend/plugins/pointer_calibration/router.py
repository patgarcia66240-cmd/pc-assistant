"""Routeur pour la persistance de la calibration et des réglages du pointeur main ARIA."""
import json
import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "pointer_calibration.json"

DEFAULT_SETTINGS = {
    "cameraWidth": 1280,
    "cameraHeight": 720,
    "detectionConfidence": 0.35,
    "presenceConfidence": 0.35,
    "trackingConfidence": 0.35,
    "verticalOffsetCm": 10.0,
    "clickFinger": "index",
    "pinchThreshold": 0.4,
}


class PointerCalibrationModel(BaseModel):
    version: int = 1
    sourceLeft: float
    sourceRight: float
    sourceTop: float
    sourceBottom: float
    targetLeft: float
    targetRight: float
    targetTop: float
    targetBottom: float


class PointerSettingsModel(BaseModel):
    cameraWidth: int = 1280
    cameraHeight: int = 720
    detectionConfidence: float = Field(default=0.35, ge=0.1, le=0.9)
    presenceConfidence: float = Field(default=0.35, ge=0.1, le=0.9)
    trackingConfidence: float = Field(default=0.35, ge=0.1, le=0.9)
    verticalOffsetCm: float = Field(default=10.0, ge=0.0, le=15.0)
    clickFinger: Literal["index", "middle", "ring", "pinky"] = "index"
    pinchThreshold: float = Field(default=0.4, ge=0.2, le=0.8)


def _load_data() -> dict:
    if DATA_PATH.exists():
        try:
            return json.loads(DATA_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            logger.warning("Fichier pointer_calibration.json corrompu (%s), réinitialisation", error)
    return {}


def _save_data(data: dict) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


@router.get("/calibration")
async def get_calibration():
    """Récupère la calibration active du pointeur (ou null si non calibré)."""
    data = _load_data()
    calibration = data.get("calibration")
    return {"calibration": calibration}


@router.post("/calibration")
async def save_calibration(calibration: PointerCalibrationModel):
    """Enregistre la calibration en 4 points après validation géométrique."""
    if (
        abs(calibration.sourceRight - calibration.sourceLeft) < 0.05
        or abs(calibration.sourceBottom - calibration.sourceTop) < 0.05
    ):
        raise HTTPException(
            status_code=422,
            detail="Zone de calibration trop étroite. Les points doivent délimiter une zone suffisante.",
        )

    data = _load_data()
    data["calibration"] = calibration.model_dump()
    _save_data(data)
    return {"status": "saved", "calibration": data["calibration"]}


@router.delete("/calibration")
async def delete_calibration():
    """Supprime la calibration actuelle."""
    data = _load_data()
    data.pop("calibration", None)
    _save_data(data)
    return {"status": "cleared", "calibration": None}


@router.get("/settings")
async def get_settings():
    """Récupère les réglages de la caméra et de détection du pointeur."""
    data = _load_data()
    settings = data.get("settings", DEFAULT_SETTINGS)
    return {"settings": settings}


@router.post("/settings")
async def save_settings(settings: PointerSettingsModel):
    """Enregistre les réglages du pointeur."""
    supported_resolutions = [(640, 480), (1280, 720), (1920, 1080)]
    if (settings.cameraWidth, settings.cameraHeight) not in supported_resolutions:
        raise HTTPException(
            status_code=422,
            detail="Résolution non supportée. Valeurs acceptées: 640x480, 1280x720, 1920x1080.",
        )

    data = _load_data()
    data["settings"] = settings.model_dump()
    _save_data(data)
    return {"status": "saved", "settings": data["settings"]}


@router.delete("/settings")
async def reset_settings():
    """Réinitialise les réglages du pointeur aux valeurs par défaut."""
    data = _load_data()
    data["settings"] = dict(DEFAULT_SETTINGS)
    _save_data(data)
    return {"status": "reset", "settings": data["settings"]}
