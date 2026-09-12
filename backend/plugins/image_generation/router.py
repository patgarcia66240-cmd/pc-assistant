"""Generate and store images with the OpenAI Images API."""
import base64
import binascii
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from config import settings
from db import async_session
from plugins.image_generation.models import GeneratedImage
from security import require_api_key


router = APIRouter()
MAX_IMAGE_BYTES = 30 * 1024 * 1024


class GenerateImageRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    size: Literal["1024x1024", "1024x1536", "1536x1024"] = "1024x1024"
    quality: Literal["low", "medium", "high"] = "medium"


def _image_payload(image: GeneratedImage) -> dict:
    return {
        "id": image.id,
        "prompt": image.prompt,
        "revised_prompt": image.revised_prompt,
        "model": image.model,
        "size": image.size,
        "quality": image.quality,
        "mime_type": image.mime_type,
        "created_at": image.created_at.isoformat(),
        "url": f"/api/images/{image.id}",
        "download_url": f"/api/images/{image.id}?download=true",
    }


def _openai_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"OpenAI a refusé la génération (HTTP {response.status_code})"
    message = payload.get("error", {}).get("message") if isinstance(payload, dict) else None
    return message or f"OpenAI a refusé la génération (HTTP {response.status_code})"


@router.get("/status", dependencies=[Depends(require_api_key)])
async def image_generation_status():
    return {
        "available": bool(settings.OPENAI_API_KEY),
        "provider": "OpenAI",
        "model": settings.OPENAI_IMAGE_MODEL,
    }


@router.post("/generate", dependencies=[Depends(require_api_key)])
async def generate_image(request: GenerateImageRequest):
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Ajoutez d’abord votre clé API OpenAI dans les paramètres d’ARIA.",
        )

    model = settings.OPENAI_IMAGE_MODEL
    endpoint = f"{settings.OPENAI_BASE_URL.rstrip('/')}/images/generations"
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "prompt": request.prompt.strip(),
                    "size": request.size,
                    "quality": request.quality,
                    "output_format": "png",
                    "n": 1,
                },
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail=_openai_error_detail(error.response),
        ) from error
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail="Le service d’images OpenAI est indisponible.") from error

    try:
        item = response.json()["data"][0]
        image_data = base64.b64decode(item["b64_json"], validate=True)
    except (ValueError, KeyError, IndexError, TypeError, binascii.Error) as error:
        raise HTTPException(status_code=502, detail="OpenAI a renvoyé une image invalide.") from error
    if not image_data or len(image_data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=502, detail="L’image renvoyée par OpenAI a une taille invalide.")

    image = GeneratedImage(
        id=str(uuid4()),
        prompt=request.prompt.strip(),
        revised_prompt=str(item.get("revised_prompt") or "").strip() or None,
        model=model,
        size=request.size,
        quality=request.quality,
        mime_type="image/png",
        data=image_data,
    )
    async with async_session() as session:
        session.add(image)
        await session.commit()
        await session.refresh(image)
    return _image_payload(image)


@router.get("", dependencies=[Depends(require_api_key)])
async def list_generated_images(limit: int = Query(default=24, ge=1, le=100)):
    async with async_session() as session:
        images = (
            await session.execute(
                select(GeneratedImage).order_by(GeneratedImage.created_at.desc()).limit(limit)
            )
        ).scalars().all()
    return {"images": [_image_payload(image) for image in images]}


@router.get("/{image_id}", dependencies=[Depends(require_api_key)])
async def generated_image(image_id: str, download: bool = Query(default=False)):
    async with async_session() as session:
        image = await session.get(GeneratedImage, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image introuvable")
    disposition = "attachment" if download else "inline"
    return Response(
        content=image.data,
        media_type=image.mime_type,
        headers={"Content-Disposition": f'{disposition}; filename="aria-{image.id}.png"'},
    )


@router.delete("/{image_id}", dependencies=[Depends(require_api_key)])
async def delete_generated_image(image_id: str):
    async with async_session() as session:
        result = await session.execute(delete(GeneratedImage).where(GeneratedImage.id == image_id))
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Image introuvable")
        await session.commit()
    return {"status": "deleted", "id": image_id}
