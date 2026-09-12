"""Chat routes with Claude API integration"""
import asyncio
import contextlib
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from uuid import uuid4
import httpx
from anthropic import APIError
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from db import async_session
from models.conversation import Conversation, Message
from services.claude_service import claude_service
from plugin_loader import get_chat_handlers

router = APIRouter()
logger = logging.getLogger(__name__)
SERVICE_ERRORS = (httpx.HTTPError, LookupError, IndexError, KeyError, ValueError, TypeError)

# Chantier de migration terminé le 12/09/2026 : TOUT ce qui était codé en dur ici (RAM,
# ville/département/région, heure/météo, bourse, agenda IA) est passé en plugin, dans le même
# ordre relatif qu'avant (voir chat_handler_order de chaque manifest : ram=10, city_info=20,
# heure_meteo=30, bourse=40, quiz=90, kings=100, calendar=200...). _chat() ne fait plus que
# parcourir PLUGIN_CHAT_HANDLERS (triés par chat_handler_order) et retomber sur Claude seul si
# aucun handler ne matche — voir plugin_loader.get_chat_handlers() pour le contrat exact.
PLUGIN_CHAT_HANDLERS = get_chat_handlers()


class ChatMessage(BaseModel):
    message: str
    context: dict = {}
    conversation_id: str | None = None


async def _persist_exchange(conversation_id: str, user_text: str, assistant_text: str) -> None:
    async with async_session() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None:
            conversation = Conversation(
                id=conversation_id,
                title=user_text.strip()[:80] or "Conversation",
            )
            session.add(conversation)
        session.add_all([
            Message(id=str(uuid4()), conversation_id=conversation_id, role="user", content=user_text),
            Message(id=str(uuid4()), conversation_id=conversation_id, role="assistant", content=assistant_text),
        ])
        conversation.updated_at = datetime.now(timezone.utc)
        await session.commit()


@router.post("/")
async def chat(message: ChatMessage):
    conversation_id = message.conversation_id or str(uuid4())
    result = await _chat(message)
    if result.get("status") == "success":
        await _persist_exchange(conversation_id, message.message, result["response"])
    result["conversation_id"] = conversation_id
    return result


@router.post("/stream")
async def chat_stream(message: ChatMessage):
    conversation_id = message.conversation_id or str(uuid4())

    async def event_stream():
        queue = asyncio.Queue()
        finished = object()

        async def emit_text(text: str) -> None:
            await queue.put({"type": "delta", "text": text})

        async def produce() -> None:
            try:
                result = await _chat(message, on_text=emit_text)
                if result.get("status") == "success":
                    await _persist_exchange(conversation_id, message.message, result["response"])
                result["conversation_id"] = conversation_id
                await queue.put({"type": "done", "data": result})
            except HTTPException as error:
                await queue.put({"type": "error", "detail": error.detail})
            finally:
                await queue.put(finished)

        producer = asyncio.create_task(produce())
        try:
            while True:
                event = await queue.get()
                if event is finished:
                    break
                yield json.dumps(event, ensure_ascii=False) + "\n"
        finally:
            if not producer.done():
                producer.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await producer

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store"},
    )


async def _chat(
    message: ChatMessage,
    on_text: Callable[[str], Awaitable[None]] | None = None,
):
    """Send message to ARIA"""
    if not message.message.strip():
        raise HTTPException(status_code=422, detail="Message cannot be empty")

    # Handlers fournis par les plugins (voir PLUGIN_CHAT_HANDLERS plus haut), triés par
    # chat_handler_order croissant. Le premier dont matches() renvoie True traite le message ;
    # une HTTPException levée par un handler (ex. 404 ville inconnue, 503 Claude non configuré)
    # remonte telle quelle, les autres erreurs de service suivent le contrat générique
    # (SERVICE_ERRORS -> 502 avec le chat_error_message du manifest).
    for handler in PLUGIN_CHAT_HANDLERS:
        if not handler["matches"](message.message):
            continue
        try:
            result = await handler["handle"](message.message, message.context)
        except SERVICE_ERRORS as error:
            raise HTTPException(status_code=502, detail=handler["error_message"]) from error
        return {**result, "context": message.context, "status": "success"}

    if not claude_service.is_configured():
        raise HTTPException(status_code=503, detail="Le fournisseur IA sélectionné n'est pas configuré")

    try:
        response = await claude_service.chat(message.message, on_text=on_text)
        return {
            "response": response,
            "context": message.context,
            "status": "success",
            "source": "ai",
        }
    except (APIError, httpx.HTTPError, IndexError, KeyError, TypeError) as error:
        if getattr(error, "status_code", None) in {401, 403}:
            raise HTTPException(status_code=502, detail="La clé API du fournisseur IA est invalide ou expirée") from error
        raise HTTPException(status_code=502, detail="La requête au fournisseur IA a échoué") from error

@router.get("/history")
async def get_history(conversation_id: str | None = None, limit: int = 100):
    """Return persisted chat history, optionally scoped to one conversation."""
    limit = max(1, min(limit, 500))
    async with async_session() as session:
        query = select(Message).order_by(Message.created_at.asc()).limit(limit)
        if conversation_id:
            query = query.where(Message.conversation_id == conversation_id)
        messages = (await session.execute(query)).scalars().all()
    return {
        "messages": [
            {
                "id": item.id,
                "conversation_id": item.conversation_id,
                "role": item.role,
                "content": item.content,
                "created_at": item.created_at.isoformat(),
            }
            for item in messages
        ]
    }
