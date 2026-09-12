"""Carnet de contacts WhatsApp/Telegram stocké dans la base SQLAlchemy principale."""
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Column, DateTime, String, select

from db import async_session
from models.conversation import Base

logger = logging.getLogger(__name__)

CONTACTS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "messaging_contacts.json"
MIGRATED_CONTACTS_PATH = CONTACTS_PATH.with_name("messaging_contacts.migrated.json")


class MessagingContact(Base):
    __tablename__ = "messaging_contacts"

    normalized_name = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    whatsapp = Column(String, nullable=True)
    telegram = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


_migration_lock = asyncio.Lock()
_migration_checked = False


def _payload(contact: MessagingContact) -> dict:
    return {
        "name": contact.name,
        "whatsapp": contact.whatsapp,
        "telegram": contact.telegram,
    }


async def _migrate_legacy_json() -> None:
    global _migration_checked
    if _migration_checked:
        return

    async with _migration_lock:
        if _migration_checked:
            return
        if not CONTACTS_PATH.exists():
            _migration_checked = True
            return
        try:
            legacy_contacts = json.loads(CONTACTS_PATH.read_text(encoding="utf-8"))
            if not isinstance(legacy_contacts, dict):
                raise ValueError("le contenu doit être un objet JSON")
        except (json.JSONDecodeError, OSError, ValueError) as error:
            logger.error("Migration du carnet JSON impossible : %s", error)
            raise RuntimeError("Le carnet de contacts historique est illisible") from error

        async with async_session() as session:
            for legacy in legacy_contacts.values():
                if not isinstance(legacy, dict) or not str(legacy.get("name", "")).strip():
                    logger.warning("Contact historique invalide ignoré pendant la migration")
                    continue
                name = str(legacy["name"]).strip()
                key = name.casefold()
                contact = await session.get(MessagingContact, key)
                if contact is None:
                    session.add(
                        MessagingContact(
                            normalized_name=key,
                            name=name,
                            whatsapp=legacy.get("whatsapp"),
                            telegram=legacy.get("telegram"),
                        )
                    )
                else:
                    contact.whatsapp = contact.whatsapp or legacy.get("whatsapp")
                    contact.telegram = contact.telegram or legacy.get("telegram")
            await session.commit()

        try:
            CONTACTS_PATH.replace(MIGRATED_CONTACTS_PATH)
        except OSError as error:
            logger.warning(
                "Contacts migrés vers SQLite, mais sauvegarde du JSON impossible : %s",
                error,
            )
        _migration_checked = True


async def list_contacts() -> list[dict]:
    await _migrate_legacy_json()
    async with async_session() as session:
        contacts = list(
            (
                await session.scalars(
                    select(MessagingContact).order_by(MessagingContact.normalized_name)
                )
            ).all()
        )
    return [_payload(contact) for contact in contacts]


async def find_contact(name: str) -> dict | None:
    await _migrate_legacy_json()
    async with async_session() as session:
        contact = await session.get(MessagingContact, name.strip().casefold())
    return _payload(contact) if contact else None


async def upsert_contact(
    name: str,
    whatsapp: str | None,
    telegram: str | None,
) -> dict:
    """Fusionne les canaux fournis avec le contact existant."""
    await _migrate_legacy_json()
    display_name = name.strip()
    key = display_name.casefold()
    async with async_session() as session:
        contact = await session.get(MessagingContact, key)
        if contact is None:
            contact = MessagingContact(
                normalized_name=key,
                name=display_name,
                whatsapp=whatsapp,
                telegram=telegram,
            )
            session.add(contact)
        else:
            contact.name = display_name
            if whatsapp is not None:
                contact.whatsapp = whatsapp
            if telegram is not None:
                contact.telegram = telegram
        await session.commit()
        await session.refresh(contact)
        return _payload(contact)


async def delete_contact(name: str) -> bool:
    await _migrate_legacy_json()
    async with async_session() as session:
        contact = await session.get(MessagingContact, name.strip().casefold())
        if contact is None:
            return False
        await session.delete(contact)
        await session.commit()
    return True
