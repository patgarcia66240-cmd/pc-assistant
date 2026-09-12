"""Pont WhatsApp : reçoit les messages entrants via un webhook interne appelé par
whatsapp-bridge/ (service Node.js séparé, à la racine du repo, qui parle à WhatsApp via
Baileys — voir whatsapp-bridge/README.md). Chaque message reçu est traité exactement comme un
message de chat normal (même fonction que POST /api/chat/, voir routes/chat.py — heure/météo,
bourse, rois de France, agenda IA, Claude en dernier recours, tout marche pareil), puis la
réponse est repostée à whatsapp-bridge/ pour être envoyée sur WhatsApp.

Sécurité (deux couches, différentes de celles du reste de l'app) :
  1. WHATSAPP_BRIDGE_SECRET : secret partagé, identique des deux côtés (backend/.env et
     whatsapp-bridge/.env). Protège POST /incoming (appelé par le pont, pas par le frontend —
     require_api_key ne s'applique pas ici) ET est renvoyé au pont sur chaque appel à /send.
  2. WHATSAPP_ALLOWED_NUMBERS : liste blanche de numéros. Vide par défaut = AUCUN message
     traité, même avec le secret correct — évite qu'ARIA réponde à n'importe qui qui
     découvrirait le numéro WhatsApp dédié. À remplir dans backend/.env une fois le numéro en
     service (voir commentaire dans .env.example).
"""
import base64
import binascii
import json
import logging
import secrets as secrets_module
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, ForeignKey, LargeBinary, String, delete, select

from config import settings
from db import async_session
from models.conversation import Base, Conversation, Message
from plugins.messaging import contacts as contacts_store
from routes.chat import chat as core_chat, ChatMessage
from security import require_api_key

router = APIRouter()
logger = logging.getLogger(__name__)
SESSIONS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "whatsapp_aria_sessions.json"
START_COMMAND = "@aria start"
STOP_COMMAND = "@aria stop"
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
DELIVERY_STATUS_RANK = {"pending": 0, "sent": 1, "delivered": 2, "read": 3}


def _should_update_delivery_status(current: str, new: str) -> bool:
    return new == "failed" or DELIVERY_STATUS_RANK.get(new, -1) >= DELIVERY_STATUS_RANK.get(current, -1)


class WhatsAppMedia(Base):
    __tablename__ = "whatsapp_media"

    id = Column(String, primary_key=True)
    message_id = Column(String, ForeignKey("messages.id"), unique=True, nullable=False, index=True)
    mime_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    data = Column(LargeBinary, nullable=False)


class WhatsAppDelivery(Base):
    __tablename__ = "whatsapp_delivery_statuses"

    whatsapp_message_id = Column(String, primary_key=True)
    status = Column(String, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class IncomingMessage(BaseModel):
    from_number: str
    message: str
    reply_enabled: bool = True
    image_base64: str | None = None
    image_mime_type: str | None = None
    image_file_name: str | None = None
    document_base64: str | None = None
    document_mime_type: str | None = None
    document_file_name: str | None = None
    audio_base64: str | None = None
    audio_mime_type: str | None = None
    audio_file_name: str | None = None
    whatsapp_message_id: str | None = None
    delivery_status: str | None = None
    from_me: bool = False


class SendMessage(BaseModel):
    to: str
    message: str


class DeliveryUpdate(BaseModel):
    message_id: str
    status: str


def _normalize_number(raw: str) -> str:
    """Normalise un numéro pour le JID WhatsApp, avec la France comme pays par défaut."""
    digits = _number_digits(raw)
    if digits.startswith("0033"):
        return digits[2:]
    if len(digits) == 10 and digits.startswith("0"):
        return f"33{digits[1:]}"
    if len(digits) == 9:
        return f"33{digits}"
    return digits


def _number_digits(raw: str) -> str:
    return "".join(ch for ch in raw.split("@")[0] if ch.isdigit())


def _allowed_numbers() -> set[str]:
    return {_normalize_number(n) for n in settings.WHATSAPP_ALLOWED_NUMBERS.split(",") if n.strip()}


def _active_sessions() -> set[str]:
    try:
        payload = json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))
        return {str(number) for number in payload if str(number).isdigit()}
    except FileNotFoundError:
        return set()
    except (json.JSONDecodeError, OSError, TypeError) as error:
        logger.error("[ARIA][WhatsApp] Sessions de conversation illisibles : %s", error)
        raise HTTPException(status_code=500, detail="État des conversations WhatsApp indisponible") from error


def _set_session_active(sender: str, active: bool) -> None:
    sessions = _active_sessions()
    if active:
        sessions.add(sender)
    else:
        sessions.discard(sender)
    SESSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        SESSIONS_PATH.write_text(
            json.dumps(sorted(sessions), ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as error:
        logger.error("[ARIA][WhatsApp] Impossible d'enregistrer les sessions : %s", error)
        raise HTTPException(status_code=500, detail="État des conversations WhatsApp indisponible") from error


async def _verify_bridge_secret(x_bridge_secret: str | None = Header(default=None)) -> None:
    if not settings.WHATSAPP_BRIDGE_SECRET:
        raise HTTPException(status_code=503, detail="WHATSAPP_BRIDGE_SECRET non configuré côté backend")
    if not x_bridge_secret or not secrets_module.compare_digest(x_bridge_secret, settings.WHATSAPP_BRIDGE_SECRET):
        raise HTTPException(status_code=403, detail="Secret de pont invalide")


async def _send_via_bridge(number: str, text: str) -> dict:
    """Lève une HTTPException 502 si l'envoi échoue — utilisé par POST /send (ajouté le
    12/09/2026 : l'app/un chat_handler qui envoie un message À LA DEMANDE doit savoir si ça a
    marché, contrairement à _send_reply ci-dessous, qui reste best-effort pour ne jamais faire
    planter le traitement d'un message entrant à cause d'un échec d'envoi de la réponse)."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{settings.WHATSAPP_BRIDGE_URL.rstrip('/')}/send",
                json={"to": number, "message": text},
                headers={"X-Bridge-Secret": settings.WHATSAPP_BRIDGE_SECRET},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"Échec de l'envoi WhatsApp : {error}") from error


async def _send_media_via_bridge(
    number: str,
    caption: str,
    data: bytes,
    mime_type: str,
    file_name: str,
    media_kind: str,
) -> dict:
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.WHATSAPP_BRIDGE_URL.rstrip('/')}/send-media",
                json={
                    "to": number,
                    "caption": caption,
                    "base64": base64.b64encode(data).decode("ascii"),
                    "mimeType": mime_type,
                    "fileName": file_name,
                    "mediaKind": media_kind,
                },
                headers={"X-Bridge-Secret": settings.WHATSAPP_BRIDGE_SECRET},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"Échec de l'envoi du document WhatsApp : {error}") from error


async def _send_reply(number: str, text: str) -> None:
    try:
        await _send_via_bridge(number, text)
    except HTTPException as error:
        logger.error("[ARIA][WhatsApp] Échec de l'envoi de la réponse à %s : %s", number, error.detail)


async def _persist_outgoing_message(
    number: str,
    text: str,
    message_id: str | None = None,
    delivery_status: str | None = None,
) -> None:
    await _persist_message(number, text, "assistant", message_id=message_id, delivery_status=delivery_status)


async def _persist_incoming_message(
    number: str,
    text: str,
    image: tuple[bytes, str, str] | None = None,
) -> None:
    await _persist_message(number, text, "user", image)


async def _persist_message(
    number: str,
    text: str,
    role: str,
    image: tuple[bytes, str, str] | None = None,
    message_id: str | None = None,
    delivery_status: str | None = None,
) -> None:
    conversation_id = f"whatsapp:{number}"
    contacts = await contacts_store.list_contacts()
    contact = next(
        (
            item
            for item in contacts
            if item.get("whatsapp") and _normalize_number(item["whatsapp"]) == number
        ),
        None,
    )
    async with async_session() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None:
            conversation = Conversation(
                id=conversation_id,
                title=f"WhatsApp · {contact['name'] if contact else number}",
            )
            session.add(conversation)
        message_id = message_id or str(uuid4())
        session.add(
            Message(id=message_id, conversation_id=conversation_id, role=role, content=text)
        )
        if delivery_status:
            status_row = await session.get(WhatsAppDelivery, message_id)
            if status_row is None:
                session.add(
                    WhatsAppDelivery(
                        whatsapp_message_id=message_id,
                        status=delivery_status,
                    )
                )
            else:
                if _should_update_delivery_status(status_row.status, delivery_status):
                    status_row.status = delivery_status
                    status_row.updated_at = datetime.now(timezone.utc)
        if image:
            data, mime_type, file_name = image
            session.add(
                WhatsAppMedia(
                    id=str(uuid4()),
                    message_id=message_id,
                    mime_type=mime_type,
                    file_name=file_name,
                    data=data,
                )
            )
        conversation.updated_at = datetime.now(timezone.utc)
        await session.commit()


@router.post("/incoming", dependencies=[Depends(_verify_bridge_secret)])
async def incoming(payload: IncomingMessage):
    sender = _normalize_number(payload.from_number)
    allowed = sender in _allowed_numbers()
    known_contact = False
    if not allowed or not payload.reply_enabled:
        contacts = await contacts_store.list_contacts()
        known_contact = any(
            contact.get("whatsapp")
            and _normalize_number(contact["whatsapp"]) == sender
            for contact in contacts
        )
    if not allowed and not known_contact and not payload.from_me:
        logger.warning("[ARIA][WhatsApp] Message ignoré (numéro non autorisé) : %s", sender)
        return {"status": "ignored", "reason": "number_not_allowed"}
    attachment = None
    if payload.image_base64 or payload.document_base64 or payload.audio_base64:
        is_image = bool(payload.image_base64)
        is_audio = bool(payload.audio_base64)
        encoded_data = (
            payload.image_base64
            if is_image
            else payload.audio_base64 if is_audio else payload.document_base64
        )
        mime_type = (
            payload.image_mime_type
            if is_image
            else payload.audio_mime_type if is_audio else payload.document_mime_type
        )
        file_name = (
            payload.image_file_name
            if is_image
            else payload.audio_file_name if is_audio else payload.document_file_name
        )
        max_bytes = MAX_IMAGE_BYTES if is_image else MAX_DOCUMENT_BYTES
        if is_image and mime_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=415, detail="Format d’image WhatsApp non pris en charge")
        try:
            attachment_data = base64.b64decode(encoded_data, validate=True)
        except (binascii.Error, ValueError) as error:
            raise HTTPException(status_code=422, detail="Fichier WhatsApp invalide") from error
        if not attachment_data or len(attachment_data) > max_bytes:
            raise HTTPException(status_code=413, detail="Fichier WhatsApp vide ou supérieur à 10 Mo")
        safe_file_name = Path(file_name or "document-whatsapp").name.replace('"', "").replace("\r", "").replace("\n", "")
        attachment = (attachment_data, mime_type or "application/octet-stream", safe_file_name)
        await _persist_message(
            sender,
            payload.message.strip() or ("Image reçue" if is_image else safe_file_name),
            "assistant" if payload.from_me else "user",
            attachment,
            message_id=payload.whatsapp_message_id,
            delivery_status=payload.delivery_status if payload.from_me else None,
        )
        return {"status": "received", "aria_session_active": False}
    if payload.from_me:
        await _persist_outgoing_message(
            sender,
            payload.message,
            payload.whatsapp_message_id,
            payload.delivery_status,
        )
        return {"status": "received", "aria_session_active": False}
    if not payload.reply_enabled or not allowed:
        await _persist_incoming_message(sender, payload.message)
        return {"status": "received", "aria_session_active": False}

    command = " ".join(payload.message.strip().casefold().split())
    if command == START_COMMAND:
        _set_session_active(sender, True)
        await _send_reply(
            sender,
            "ARIA est activée. Tu peux maintenant discuter avec moi. Envoie « @aria stop » pour arrêter.",
        )
        return {"status": "started"}
    if command == STOP_COMMAND:
        _set_session_active(sender, False)
        await _send_reply(sender, "ARIA est arrêtée. Envoie « @aria start » pour reprendre la conversation.")
        return {"status": "stopped"}
    if sender not in _active_sessions():
        await _persist_incoming_message(sender, payload.message)
        return {"status": "received", "aria_session_active": False}

    # conversation_id dérivé du numéro : chaque contact WhatsApp garde son propre historique
    # dans la table conversations (visible aussi depuis /api/chat/history?conversation_id=...),
    # séparé des conversations démarrées depuis l'app.
    chat_message = ChatMessage(
        message=payload.message,
        context={},
        conversation_id=f"whatsapp:{sender}",
    )
    try:
        result = await core_chat(chat_message)
        reply_text = result.get("response") or "…"
    except HTTPException as error:
        logger.error("[ARIA][WhatsApp] Échec du traitement du message de %s : %s", sender, error.detail)
        reply_text = "Désolée, je n'ai pas pu traiter ce message pour le moment."

    await _send_reply(sender, reply_text)
    return {"status": "handled"}


@router.post("/delivery", dependencies=[Depends(_verify_bridge_secret)])
async def update_delivery(payload: DeliveryUpdate):
    allowed_statuses = {"pending", "sent", "delivered", "read", "failed"}
    if payload.status not in allowed_statuses:
        raise HTTPException(status_code=422, detail="Statut de livraison WhatsApp invalide")
    async with async_session() as session:
        status_row = await session.get(WhatsAppDelivery, payload.message_id)
        if status_row is None:
            status_row = WhatsAppDelivery(
                whatsapp_message_id=payload.message_id,
                status=payload.status,
            )
            session.add(status_row)
        else:
            if _should_update_delivery_status(status_row.status, payload.status):
                status_row.status = payload.status
                status_row.updated_at = datetime.now(timezone.utc)
        await session.commit()
    return {"status": "updated"}


@router.post("/send", dependencies=[Depends(require_api_key)])
async def send(payload: SendMessage):
    """Envoi À LA DEMANDE, depuis l'app (require_api_key, pas le secret de pont) — ajouté le
    12/09/2026 pour piloter WhatsApp depuis les onglets Chat/Vocal (voir plugins/messaging/
    chat_handler.py, "envoie un message whatsapp à ... disant ..."). Différent de POST /incoming
    (appelé par whatsapp-bridge/, jamais par l'app) : ici c'est ARIA qui prend l'initiative
    d'envoyer, pas une réponse à un message reçu."""
    if not settings.WHATSAPP_BRIDGE_SECRET:
        raise HTTPException(status_code=503, detail="WhatsApp non configuré (secret de pont manquant)")
    number = _normalize_number(payload.to)
    if not number:
        raise HTTPException(status_code=422, detail="Numéro de destinataire invalide")
    if not payload.message.strip():
        raise HTTPException(status_code=422, detail="Message vide")
    text = payload.message.strip()
    bridge_result = await _send_via_bridge(number, text)
    await _persist_outgoing_message(
        number,
        text,
        bridge_result.get("messageId"),
        bridge_result.get("deliveryStatus", "pending"),
    )
    return {"status": "sent", "to": number}


@router.post("/send-document", dependencies=[Depends(require_api_key)])
@router.post("/send-media", dependencies=[Depends(require_api_key)])
async def send_media(
    to: str = Form(...),
    message: str = Form(default=""),
    document: UploadFile = File(...),
):
    if not settings.WHATSAPP_BRIDGE_SECRET:
        raise HTTPException(status_code=503, detail="WhatsApp non configuré (secret de pont manquant)")
    number = _normalize_number(to)
    if not number:
        raise HTTPException(status_code=422, detail="Numéro de destinataire invalide")
    file_name = Path(document.filename or "").name.replace('"', "").replace("\r", "").replace("\n", "")
    if not file_name:
        raise HTTPException(status_code=422, detail="Nom de document invalide")
    data = await document.read(MAX_DOCUMENT_BYTES + 1)
    if not data or len(data) > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="Le document doit faire entre 1 octet et 10 Mo")
    mime_type = document.content_type or "application/octet-stream"
    caption = message.strip()
    if mime_type in ALLOWED_IMAGE_TYPES:
        media_kind = "image"
    elif mime_type.startswith("audio/"):
        media_kind = "audio"
    else:
        media_kind = "document"
    bridge_result = await _send_media_via_bridge(number, caption, data, mime_type, file_name, media_kind)
    await _persist_message(
        number,
        file_name if media_kind == "audio" else caption or file_name,
        "assistant",
        (data, mime_type, file_name),
        message_id=bridge_result.get("messageId"),
        delivery_status=bridge_result.get("deliveryStatus", "pending"),
    )
    if media_kind == "audio" and caption:
        await _persist_outgoing_message(
            number,
            caption,
            bridge_result.get("captionMessageId"),
            bridge_result.get("captionDeliveryStatus", "pending"),
        )
    return {"status": "sent", "to": number, "file_name": file_name, "media_kind": media_kind}


@router.get("/conversations", dependencies=[Depends(require_api_key)])
async def list_conversations():
    contacts = await contacts_store.list_contacts()
    names_by_number = {
        _normalize_number(contact["whatsapp"]): contact["name"]
        for contact in contacts
        if contact.get("whatsapp")
    }
    active_sessions = _active_sessions()
    async with async_session() as session:
        conversations = list(
            (
                await session.scalars(
                    select(Conversation)
                    .where(Conversation.id.like("whatsapp:%"))
                    .order_by(Conversation.updated_at.desc())
                )
            ).all()
        )
        result = []
        for conversation in conversations:
            number = conversation.id.removeprefix("whatsapp:")
            last_message = (
                await session.scalars(
                    select(Message)
                    .where(Message.conversation_id == conversation.id)
                    .order_by(Message.created_at.desc())
                    .limit(1)
                )
            ).first()
            result.append(
                {
                    "number": number,
                    "name": names_by_number.get(number, number),
                    "updated_at": conversation.updated_at.isoformat(),
                    "last_message": last_message.content if last_message else "",
                    "last_role": last_message.role if last_message else None,
                    "aria_active": number in active_sessions,
                }
            )
    return {"conversations": result}


@router.get("/conversations/{number}", dependencies=[Depends(require_api_key)])
async def conversation_messages(number: str):
    stored_number = _number_digits(number)
    if not stored_number:
        raise HTTPException(status_code=422, detail="Numéro WhatsApp invalide")
    async with async_session() as session:
        messages = list(
            (
                await session.scalars(
                    select(Message)
                    .where(Message.conversation_id == f"whatsapp:{stored_number}")
                    .order_by(Message.created_at.desc())
                    .limit(100)
                )
            ).all()
        )
        media_rows = list(
            (
                await session.scalars(
                    select(WhatsAppMedia).where(
                        WhatsAppMedia.message_id.in_([message.id for message in messages])
                    )
                )
            ).all()
        ) if messages else []
        delivery_rows = list(
            (
                await session.scalars(
                    select(WhatsAppDelivery).where(
                        WhatsAppDelivery.whatsapp_message_id.in_([message.id for message in messages])
                    )
                )
            ).all()
        ) if messages else []
    media_by_message = {media.message_id: media for media in media_rows}
    delivery_by_message = {
        delivery.whatsapp_message_id: delivery.status
        for delivery in delivery_rows
    }
    return {
        "number": stored_number,
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
                "delivery_status": delivery_by_message.get(message.id),
                "image": (
                    {
                        "url": f"/api/whatsapp/media/{media_by_message[message.id].id}",
                        "file_name": media_by_message[message.id].file_name,
                        "mime_type": media_by_message[message.id].mime_type,
                    }
                    if message.id in media_by_message
                    and media_by_message[message.id].mime_type.startswith("image/")
                    else None
                ),
                "document": (
                    {
                        "url": f"/api/whatsapp/media/{media_by_message[message.id].id}",
                        "file_name": media_by_message[message.id].file_name,
                        "mime_type": media_by_message[message.id].mime_type,
                    }
                    if message.id in media_by_message
                    and not media_by_message[message.id].mime_type.startswith("image/")
                    and not media_by_message[message.id].mime_type.startswith("audio/")
                    else None
                ),
                "audio": (
                    {
                        "url": f"/api/whatsapp/media/{media_by_message[message.id].id}",
                        "file_name": media_by_message[message.id].file_name,
                        "mime_type": media_by_message[message.id].mime_type,
                    }
                    if message.id in media_by_message
                    and media_by_message[message.id].mime_type.startswith("audio/")
                    else None
                ),
            }
            for message in reversed(messages)
        ],
    }


@router.get("/media/{media_id}", dependencies=[Depends(require_api_key)])
async def whatsapp_media(media_id: str, download: bool = Query(default=False)):
    async with async_session() as session:
        media = await session.get(WhatsAppMedia, media_id)
    if media is None:
        raise HTTPException(status_code=404, detail="Fichier WhatsApp introuvable")
    disposition = "attachment" if download else "inline"
    return Response(
        content=media.data,
        media_type=media.mime_type,
        headers={"Content-Disposition": f'{disposition}; filename="{media.file_name}"'},
    )


@router.delete("/conversations/{number}", dependencies=[Depends(require_api_key)])
async def delete_conversation(number: str):
    stored_number = _number_digits(number)
    if not stored_number:
        raise HTTPException(status_code=422, detail="Numéro WhatsApp invalide")
    conversation_id = f"whatsapp:{stored_number}"
    async with async_session() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation WhatsApp introuvable")
        message_ids = select(Message.id).where(Message.conversation_id == conversation_id)
        await session.execute(delete(WhatsAppMedia).where(WhatsAppMedia.message_id.in_(message_ids)))
        await session.execute(
            delete(WhatsAppDelivery).where(WhatsAppDelivery.whatsapp_message_id.in_(message_ids))
        )
        await session.execute(delete(Message).where(Message.conversation_id == conversation_id))
        await session.delete(conversation)
        await session.commit()
    return {"status": "deleted", "number": stored_number}


@router.get("/contacts", dependencies=[Depends(require_api_key)])
async def bridge_contacts():
    """Contacts synchronisés depuis le téléphone lié à ARIA (nom + numéro), via l'évènement
    Baileys contacts.upsert/contacts.update (voir whatsapp-bridge/index.js) — ajouté le
    12/09/2026 pour les importer en un clic dans le carnet de plugins/messaging/ (voir
    contacts.py) plutôt que de les taper à la main. Différent de GET /api/messaging/contacts
    (le carnet lui-même, propre à ARIA) : ceci est la liste BRUTE côté WhatsApp, en lecture
    seule, jamais persistée par ce plugin. Peut être incomplète juste après la connexion
    (la synchronisation prend quelques instants) — pas une erreur en soi."""
    if not settings.WHATSAPP_BRIDGE_SECRET:
        raise HTTPException(status_code=503, detail="WhatsApp non configuré (secret de pont manquant)")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{settings.WHATSAPP_BRIDGE_URL.rstrip('/')}/contacts",
                headers={"X-Bridge-Secret": settings.WHATSAPP_BRIDGE_SECRET},
            )
            response.raise_for_status()
            bridge_contacts = response.json()
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"Échec de récupération des contacts WhatsApp : {error}") from error
    return {"contacts": bridge_contacts.get("contacts", [])}


@router.get("/status", dependencies=[Depends(require_api_key)])
async def status():
    """Diagnostic rapide depuis l'app (pas depuis le pont) : le plugin est-il configuré, et le
    pont Node.js répond-il ?"""
    if not settings.WHATSAPP_BRIDGE_SECRET:
        return {"configured": False, "reason": "WHATSAPP_BRIDGE_SECRET manquant"}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{settings.WHATSAPP_BRIDGE_URL.rstrip('/')}/status")
            response.raise_for_status()
            bridge_status = response.json()
    except httpx.HTTPError as error:
        return {"configured": True, "bridge_reachable": False, "error": str(error)}
    return {"configured": True, "bridge_reachable": True, **bridge_status}
