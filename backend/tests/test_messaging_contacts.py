import asyncio
import json
from uuid import uuid4

from sqlalchemy import delete

from db import async_session, init_db
from plugins.messaging import contacts
from plugins.messaging.contacts import MessagingContact


def test_contacts_migrate_to_sqlite_and_merge_channels(monkeypatch, tmp_path):
    name = f"Contact-{uuid4()}"
    legacy_path = tmp_path / "messaging_contacts.json"
    migrated_path = tmp_path / "messaging_contacts.migrated.json"
    legacy_path.write_text(
        json.dumps(
            {
                name.casefold(): {
                    "name": name,
                    "whatsapp": "33612345678",
                    "telegram": None,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(contacts, "CONTACTS_PATH", legacy_path)
    monkeypatch.setattr(contacts, "MIGRATED_CONTACTS_PATH", migrated_path)
    monkeypatch.setattr(contacts, "_migration_checked", False)

    async def scenario():
        await init_db()
        listed = await contacts.list_contacts()
        assert next(item for item in listed if item["name"] == name)["whatsapp"] == "33612345678"
        assert not legacy_path.exists()
        assert migrated_path.exists()

        merged = await contacts.upsert_contact(name, None, "123456789")
        assert merged == {
            "name": name,
            "whatsapp": "33612345678",
            "telegram": "123456789",
        }
        assert await contacts.find_contact(name.upper()) == merged
        assert await contacts.delete_contact(name)
        assert await contacts.find_contact(name) is None

        async with async_session() as session:
            await session.execute(
                delete(MessagingContact).where(MessagingContact.normalized_name == name.casefold())
            )
            await session.commit()

    asyncio.run(scenario())
