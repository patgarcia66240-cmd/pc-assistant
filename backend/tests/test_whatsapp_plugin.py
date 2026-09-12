import asyncio
import base64
from io import BytesIO
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select

from db import async_session, init_db
from models.conversation import Conversation, Message
from plugins.whatsapp import router as whatsapp_router
from plugins.whatsapp.router import DeliveryUpdate, IncomingMessage, SendMessage


def test_whatsapp_conversation_requires_start_and_stops(monkeypatch, tmp_path):
    replies = []
    chat_messages = []
    received_messages = []

    async def fake_send_reply(number, text):
        replies.append((number, text))

    async def fake_core_chat(message):
        chat_messages.append(message.message)
        return {"response": "Réponse ARIA"}

    async def fake_persist_incoming(number, text):
        received_messages.append((number, text))

    monkeypatch.setattr(whatsapp_router, "SESSIONS_PATH", tmp_path / "sessions.json")
    monkeypatch.setattr(whatsapp_router.settings, "WHATSAPP_ALLOWED_NUMBERS", "33612345678")
    monkeypatch.setattr(whatsapp_router, "_send_reply", fake_send_reply)
    monkeypatch.setattr(whatsapp_router, "core_chat", fake_core_chat)
    monkeypatch.setattr(whatsapp_router, "_persist_incoming_message", fake_persist_incoming)

    async def scenario():
        inactive = await whatsapp_router.incoming(
            IncomingMessage(from_number="33612345678@s.whatsapp.net", message="Bonjour")
        )
        started = await whatsapp_router.incoming(
            IncomingMessage(from_number="33612345678@s.whatsapp.net", message="  @ARIA   START ")
        )
        handled = await whatsapp_router.incoming(
            IncomingMessage(from_number="33612345678@s.whatsapp.net", message="Bonjour ARIA")
        )
        stopped = await whatsapp_router.incoming(
            IncomingMessage(from_number="33612345678@s.whatsapp.net", message="@aria stop")
        )
        inactive_again = await whatsapp_router.incoming(
            IncomingMessage(from_number="33612345678@s.whatsapp.net", message="Tu es là ?")
        )
        return inactive, started, handled, stopped, inactive_again

    inactive, started, handled, stopped, inactive_again = asyncio.run(scenario())

    assert inactive == {"status": "received", "aria_session_active": False}
    assert started == {"status": "started"}
    assert handled == {"status": "handled"}
    assert stopped == {"status": "stopped"}
    assert inactive_again == {"status": "received", "aria_session_active": False}
    assert chat_messages == ["Bonjour ARIA"]
    assert received_messages == [
        ("33612345678", "Bonjour"),
        ("33612345678", "Tu es là ?"),
    ]
    assert len(replies) == 3


def test_whatsapp_message_from_saved_contact_is_received(monkeypatch, tmp_path):
    received_messages = []

    async def fake_contacts():
        return [{"name": "Thomas", "whatsapp": "764360601", "telegram": None}]

    async def fake_persist_incoming(number, text):
        received_messages.append((number, text))

    monkeypatch.setattr(whatsapp_router, "SESSIONS_PATH", tmp_path / "sessions.json")
    monkeypatch.setattr(whatsapp_router.settings, "WHATSAPP_ALLOWED_NUMBERS", "")
    monkeypatch.setattr(whatsapp_router.contacts_store, "list_contacts", fake_contacts)
    monkeypatch.setattr(whatsapp_router, "_persist_incoming_message", fake_persist_incoming)

    result = asyncio.run(
        whatsapp_router.incoming(
            IncomingMessage(
                from_number="33764360601@s.whatsapp.net",
                message="Salut, je vais bien",
            )
        )
    )

    assert result == {"status": "received", "aria_session_active": False}
    assert received_messages == [("33764360601", "Salut, je vais bien")]


def test_whatsapp_append_message_never_triggers_aria_reply(monkeypatch, tmp_path):
    received_messages = []
    replies = []

    async def fake_contacts():
        return [{"name": "Thomas", "whatsapp": "764360601", "telegram": None}]

    async def fake_persist_incoming(number, text):
        received_messages.append((number, text))

    async def fake_send_reply(number, text):
        replies.append((number, text))

    monkeypatch.setattr(whatsapp_router, "SESSIONS_PATH", tmp_path / "sessions.json")
    monkeypatch.setattr(whatsapp_router.settings, "WHATSAPP_ALLOWED_NUMBERS", "33764360601")
    monkeypatch.setattr(whatsapp_router.contacts_store, "list_contacts", fake_contacts)
    monkeypatch.setattr(whatsapp_router, "_persist_incoming_message", fake_persist_incoming)
    monkeypatch.setattr(whatsapp_router, "_send_reply", fake_send_reply)
    whatsapp_router._set_session_active("33764360601", True)

    result = asyncio.run(
        whatsapp_router.incoming(
            IncomingMessage(
                from_number="33764360601@s.whatsapp.net",
                message="Réponse historique",
                reply_enabled=False,
            )
        )
    )

    assert result == {"status": "received", "aria_session_active": False}
    assert received_messages == [("33764360601", "Réponse historique")]
    assert replies == []


def test_whatsapp_image_is_stored_and_downloadable(monkeypatch):
    number = f"337{str(uuid4().int)[:8]}"
    image_data = b"\x89PNG\r\n\x1a\naria-test"

    async def fake_contacts():
        return [{"name": "Image test", "whatsapp": number, "telegram": None}]

    monkeypatch.setattr(whatsapp_router.settings, "WHATSAPP_ALLOWED_NUMBERS", "")
    monkeypatch.setattr(whatsapp_router.contacts_store, "list_contacts", fake_contacts)

    async def scenario():
        await init_db()
        result = await whatsapp_router.incoming(
            IncomingMessage(
                from_number=f"{number}@s.whatsapp.net",
                message="Photo test",
                reply_enabled=False,
                image_base64=base64.b64encode(image_data).decode("ascii"),
                image_mime_type="image/png",
                image_file_name="photo-test.png",
            )
        )
        history = await whatsapp_router.conversation_messages(number)
        image = history["messages"][0]["image"]
        response = await whatsapp_router.whatsapp_media(image["url"].rsplit("/", 1)[-1])
        await whatsapp_router.delete_conversation(number)
        return result, history, response

    result, history, response = asyncio.run(scenario())

    assert result == {"status": "received", "aria_session_active": False}
    assert history["messages"][0]["content"] == "Photo test"
    assert history["messages"][0]["image"]["file_name"] == "photo-test.png"
    assert response.body == image_data
    assert response.media_type == "image/png"


def test_forwarded_whatsapp_image_is_stored_as_outgoing(monkeypatch):
    number = f"337{str(uuid4().int)[:8]}"

    async def fake_contacts():
        return [{"name": "Image test", "whatsapp": number, "telegram": None}]

    monkeypatch.setattr(whatsapp_router.settings, "WHATSAPP_ALLOWED_NUMBERS", "")
    monkeypatch.setattr(whatsapp_router.contacts_store, "list_contacts", fake_contacts)

    async def scenario():
        await init_db()
        result = await whatsapp_router.incoming(
            IncomingMessage(
                from_number=f"{number}@s.whatsapp.net",
                message="",
                reply_enabled=False,
                image_base64=base64.b64encode(b"forwarded-image").decode("ascii"),
                image_mime_type="image/jpeg",
                image_file_name="image-transferee.jpg",
                from_me=True,
            )
        )
        history = await whatsapp_router.conversation_messages(number)
        await whatsapp_router.delete_conversation(number)
        return result, history

    result, history = asyncio.run(scenario())

    assert result == {"status": "received", "aria_session_active": False}
    assert history["messages"][0]["role"] == "assistant"
    assert history["messages"][0]["image"]["file_name"] == "image-transferee.jpg"


def test_text_sent_from_whatsapp_is_stored_as_outgoing(monkeypatch):
    number = f"337{str(uuid4().int)[:8]}"

    async def fake_contacts():
        return []

    monkeypatch.setattr(whatsapp_router.settings, "WHATSAPP_ALLOWED_NUMBERS", "")
    monkeypatch.setattr(whatsapp_router.contacts_store, "list_contacts", fake_contacts)

    async def scenario():
        await init_db()
        result = await whatsapp_router.incoming(
            IncomingMessage(
                from_number=f"{number}@s.whatsapp.net",
                message="Message envoyé depuis WhatsApp",
                reply_enabled=False,
                from_me=True,
            )
        )
        history = await whatsapp_router.conversation_messages(number)
        await whatsapp_router.delete_conversation(number)
        return result, history

    result, history = asyncio.run(scenario())

    assert result == {"status": "received", "aria_session_active": False}
    assert [(message["role"], message["content"]) for message in history["messages"]] == [
        ("assistant", "Message envoyé depuis WhatsApp"),
    ]


def test_whatsapp_document_is_sent_stored_and_downloadable(monkeypatch):
    number = f"337{str(uuid4().int)[:8]}"
    whatsapp_message_id = f"doc-{uuid4()}"
    document_data = b"%PDF-1.4 aria document"
    sent = []

    async def fake_send(number_value, caption, data, mime_type, file_name, media_kind):
        sent.append((number_value, caption, data, mime_type, file_name, media_kind))
        return {
            "messageId": whatsapp_message_id,
            "deliveryStatus": "pending",
        }

    monkeypatch.setattr(whatsapp_router.settings, "WHATSAPP_BRIDGE_SECRET", "test-secret")
    monkeypatch.setattr(whatsapp_router, "_send_media_via_bridge", fake_send)

    async def scenario():
        await init_db()
        result = await whatsapp_router.send_media(
            to=number,
            message="Voici le document",
            document=UploadFile(
                filename="document.pdf",
                file=BytesIO(document_data),
                headers={"content-type": "application/pdf"},
            ),
        )
        history = await whatsapp_router.conversation_messages(number)
        stored_document = history["messages"][0]["document"]
        response = await whatsapp_router.whatsapp_media(
            stored_document["url"].rsplit("/", 1)[-1],
            download=True,
        )
        await whatsapp_router.delete_conversation(number)
        return result, history, response

    result, history, response = asyncio.run(scenario())

    assert result == {
        "status": "sent",
        "to": number,
        "file_name": "document.pdf",
        "media_kind": "document",
    }
    assert sent == [
        (number, "Voici le document", document_data, "application/pdf", "document.pdf", "document")
    ]
    assert history["messages"][0]["role"] == "assistant"
    assert history["messages"][0]["delivery_status"] == "pending"
    assert history["messages"][0]["document"]["file_name"] == "document.pdf"
    assert response.body == document_data
    assert response.media_type == "application/pdf"


def test_whatsapp_audio_is_sent_as_native_audio(monkeypatch):
    number = f"337{str(uuid4().int)[:8]}"
    audio_message_id = f"audio-{uuid4()}"
    caption_message_id = f"caption-{uuid4()}"
    audio_data = b"ID3 aria audio"
    sent = []

    async def fake_send(number_value, caption, data, mime_type, file_name, media_kind):
        sent.append((number_value, caption, data, mime_type, file_name, media_kind))
        return {
            "messageId": audio_message_id,
            "captionMessageId": caption_message_id,
            "deliveryStatus": "sent",
            "captionDeliveryStatus": "sent",
        }

    monkeypatch.setattr(whatsapp_router.settings, "WHATSAPP_BRIDGE_SECRET", "test-secret")
    monkeypatch.setattr(whatsapp_router, "_send_media_via_bridge", fake_send)

    async def scenario():
        await init_db()
        result = await whatsapp_router.send_media(
            to=number,
            message="Écoute ceci",
            document=UploadFile(
                filename="audio.mp3",
                file=BytesIO(audio_data),
                headers={"content-type": "audio/mpeg"},
            ),
        )
        history = await whatsapp_router.conversation_messages(number)
        await whatsapp_router.delete_conversation(number)
        return result, history

    result, history = asyncio.run(scenario())

    assert result["media_kind"] == "audio"
    assert sent == [(number, "Écoute ceci", audio_data, "audio/mpeg", "audio.mp3", "audio")]
    assert history["messages"][0]["audio"]["file_name"] == "audio.mp3"
    assert history["messages"][0]["delivery_status"] == "sent"
    assert history["messages"][1]["content"] == "Écoute ceci"
    assert history["messages"][1]["delivery_status"] == "sent"


def test_whatsapp_form_send_is_persisted(monkeypatch):
    local_number = f"7{str(uuid4().int)[:8]}"
    number = f"33{local_number}"
    sent = []

    async def fake_send(number_value, text):
        sent.append((number_value, text))
        return {"messageId": f"text-{number}", "deliveryStatus": "pending"}

    monkeypatch.setattr(whatsapp_router.settings, "WHATSAPP_BRIDGE_SECRET", "test-secret")
    monkeypatch.setattr(whatsapp_router, "_send_via_bridge", fake_send)

    async def scenario():
        await init_db()
        result = await whatsapp_router.send(SendMessage(to=local_number, message=" Bonjour "))
        await whatsapp_router.update_delivery(
            DeliveryUpdate(message_id=f"text-{number}", status="delivered")
        )
        history = await whatsapp_router.conversation_messages(number)
        async with async_session() as session:
            messages = list(
                (
                    await session.scalars(
                        select(Message).where(Message.conversation_id == f"whatsapp:{number}")
                    )
                ).all()
            )
        deleted = await whatsapp_router.delete_conversation(number)
        async with async_session() as session:
            remaining_conversation = await session.get(Conversation, f"whatsapp:{number}")
            remaining_messages = list(
                (
                    await session.scalars(
                        select(Message).where(Message.conversation_id == f"whatsapp:{number}")
                    )
                ).all()
            )
        return result, messages, history, deleted, remaining_conversation, remaining_messages

    result, messages, history, deleted, remaining_conversation, remaining_messages = asyncio.run(scenario())

    assert result == {"status": "sent", "to": number}
    assert sent == [(number, "Bonjour")]
    assert [(message.role, message.content) for message in messages] == [("assistant", "Bonjour")]
    assert history["messages"][0]["delivery_status"] == "delivered"
    assert deleted == {"status": "deleted", "number": number}
    assert remaining_conversation is None
    assert remaining_messages == []
