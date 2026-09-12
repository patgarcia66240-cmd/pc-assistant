"""Handler de chat pour piloter WhatsApp/Telegram en langage naturel depuis les onglets Chat ET
Vocal — les deux passent par POST /api/chat (voir routes/chat.py et VoiceAssistant.jsx, qui
transcrit la voix en texte puis appelle exactement le même endpoint) : un seul handler suffit
donc pour les deux, pas besoin de code séparé pour le vocal. Ajouté le 12/09/2026 à la demande
de Sarah.

Trois intentions reconnues :
  1. Envoi : verbe d'envoi + canal (whatsapp/telegram) + destinataire + marqueur de message
     ("disant", ":"...) + texte. Ex. "envoie un message whatsapp à Sophie disant je serai en retard".
     Cas particulier "envoie-moi" (destinataire = Sarah elle-même, résolu via les identifiants
     autorisés déjà configurés) — sans texte donné, on demande le contenu au lieu de deviner ou
     d'envoyer un message vide. Ajouté le 12/09/2026 après un essai réel ("envoi moi un message
     sur whatsapp") qui ne correspondait à aucun des deux cas d'origine (ni "envoie" avec un e
     final, ni un destinataire nommé introduit par "à/au").
  2. Historique : mention de messages/discussion + un mot indiquant qu'on veut les derniers +
     canal, avec un destinataire optionnel ("avec ..."). Ex. "les derniers mots de la discussion
     avec Sophie sur WhatsApp", "mes messages telegram".
  3. Carnet de contacts : "mes/les contacts" (+ canal optionnel) — ajouté le 12/09/2026 après un
     essai de Sarah ("liste de mes contact whatsapp") qui ne correspondait à aucune des deux
     intentions ci-dessus (ni un envoi, ni une demande d'historique). Contrairement aux deux
     autres, ne nécessite pas de canal explicite : "mes contacts" tout court liste tout.

Reconnaissance volontairement simple (regex décomposées, pas un unique motif rigide — corrigé le
12/09/2026 après un premier essai de Sarah qui ne correspondait pas au motif trop strict de la V1),
dans le même esprit que les autres chat_handlers du projet (heure_meteo, bourse...) : pas d'appel
à Claude pour détecter l'intention. Reste forcément incomplet face à la variété du langage naturel
— si une formulation ne matche toujours pas, l'ajuster ici plutôt que d'essayer de tout prévoir
d'avance.

Destinataire : un numéro/identifiant écrit en toutes lettres fonctionne toujours, MAIS peut aussi
être un nom du carnet de contacts (voir contacts.py, géré depuis l'onglet Messagerie) — c'est ce
qui manquait au tout premier essai ("Sophie" n'était nulle part enregistré)."""
import re

import httpx
from sqlalchemy import select

from config import settings
from db import async_session
from models.conversation import Message

from . import contacts as contacts_store

CHANNEL_PATTERN = re.compile(r"\b(whatsapp|telegram)\b", re.IGNORECASE)
# "envoies?" seul ratait la forme "envoi" (sans e) que Sarah utilise naturellement à l'impératif
# ("envoi moi un message...") — élargi le 12/09/2026 après un essai réel qui n'a pas matché.
SEND_TRIGGER = re.compile(r"\benvoi(?:e|es)?\b", re.IGNORECASE)
SEND_DETAIL = re.compile(
    r"(?:au|à|a)\s+(?P<to>.+?)\s*(?:disant|qui dit|en disant|pour dire|:)\s*(?P<text>.+)",
    re.IGNORECASE | re.DOTALL,
)
# "envoie-moi"/"envoi moi"/"envoies moi-même" : destinataire = Sarah elle-même, sans "à/au" devant
# "moi" (on ne dit pas "envoie à moi") — SEND_DETAIL ne peut donc pas matcher ce cas. Ajouté le
# 12/09/2026, toujours suite au même essai réel ("envoi moi un message sur whatsapp").
SELF_SEND = re.compile(r"\benvoi(?:e|es)?[\s-]+moi(?:[\s-]m[êe]me)?\b", re.IGNORECASE)
# Contenu du message pour un envoi à soi-même : mêmes marqueurs que SEND_DETAIL mais sans exiger
# de destinataire explicite avant. Optionnel : "envoi moi un message sur whatsapp" tout court n'en
# a pas — dans ce cas on demande le contenu plutôt que d'envoyer un message vide ou inventé.
CONTENT_MARKER = re.compile(
    r"(?:disant|qui dit|en disant|pour dire|:)\s*(?P<text>.+)",
    re.IGNORECASE | re.DOTALL,
)
# "mes/les/tes messages", ou "messages/mots/discussion" + "dernier(s)" dans un ordre ou l'autre,
# ou "montre/affiche/résume ... messages" — couvre "mes derniers messages", "les derniers mots de
# la discussion", "montre-moi les messages avec X". "qu'est-ce que X m'a dit/écrit" est une
# quatrième façon de demander la même chose.
HISTORY_TRIGGER = re.compile(
    r"\b(?:mes|les|tes|ses)\b.{0,20}\b(?:messages?|mots|discussions?|conversations?)\b"
    r"|\b(?:messages?|mots|discussions?|conversations?)\b.{0,20}\b(?:derniers?|dernière)\b"
    r"|\b(?:derniers?|dernière)\b.{0,20}\b(?:messages?|mots|discussions?|conversations?)\b"
    r"|\b(?:montre|montre-moi|affiche|résume|résumé)\b.{0,25}\b(?:messages?|mots|discussions?|conversations?)\b"
    r"|\bqu['’]?\s*est[- ]ce que\b.+\b(?:m['’]a dit|a dit|a écrit|a envoyé)\b",
    re.IGNORECASE | re.DOTALL,
)
# "avec X" est un marqueur de contact fiable ; "de X" ne l'est pas ("de la discussion", "de
# messages" — "de" est trop ambigu en français pour servir de déclencheur ici). Repli sur
# "qu'est-ce que X (m')a dit/écrit" pour la formulation en question, qui n'utilise jamais "avec".
HISTORY_CONTACT = re.compile(r"\bavec\s+(?P<contact>.+)", re.IGNORECASE)
HISTORY_QUESTION_CONTACT = re.compile(
    r"\bque\s+(?P<contact>.+?)\s+(?:m['’]a dit|a dit|a écrit|a envoyé)\b", re.IGNORECASE
)
# "mes/les contacts", ou "contacts" proche du nom d'un canal, ou "liste/montre/affiche ... contacts"
# — volontairement PAS de canal obligatoire ("mes contacts" tout court a un sens, contrairement aux
# deux intentions ci-dessus qui portent toujours sur un canal précis).
CONTACTS_TRIGGER = re.compile(
    r"\b(?:mes|les)\b.{0,15}\bcontacts?\b"
    r"|\bcontacts?\b.{0,15}\b(?:whatsapp|telegram)\b"
    r"|\b(?:liste|montre|affiche)\b.{0,20}\bcontacts?\b",
    re.IGNORECASE,
)
WHATSAPP_OPEN_TRIGGER = re.compile(
    r"^\s*(?:(?:ouvre|ouvrir|affiche|lance|va\s+sur)\s+)?"
    r"(?:le\s+)?(?:plugin\s+)?whatsapp\s*[.!?]?\s*$",
    re.IGNORECASE,
)


def _extract_channel(message: str) -> str | None:
    match = CHANNEL_PATTERN.search(message)
    return match.group(1).lower() if match else None


def _is_send(message: str) -> bool:
    return bool(SEND_TRIGGER.search(message) and (SEND_DETAIL.search(message) or SELF_SEND.search(message)))


def _is_history(message: str) -> bool:
    return bool(HISTORY_TRIGGER.search(message))


def _is_contacts(message: str) -> bool:
    return bool(CONTACTS_TRIGGER.search(message))


def matches(message: str) -> bool:
    if WHATSAPP_OPEN_TRIGGER.match(message):
        return True
    if _is_contacts(message):
        return True
    if not _extract_channel(message):
        return False
    return _is_send(message) or _is_history(message)


def _clean_number(raw: str) -> str:
    return "".join(ch for ch in raw if ch.isdigit())


def _strip_channel_mentions(raw: str) -> str:
    """Enlève "sur whatsapp"/"via telegram" etc. en bout de phrase, laissé par les regex qui ne
    s'arrêtent pas pile avant le nom du canal (ex. destinataire extrait d'une phrase qui se
    termine par "... sur WhatsApp ?")."""
    cleaned = re.sub(r"\s*(?:sur|via)\s+(?:whatsapp|telegram)\s*\??\s*$", "", raw, flags=re.IGNORECASE)
    return cleaned.strip(" ?.!\"'")


def _own_identifier(channel: str) -> str | None:
    """Le numéro/identifiant de Sarah elle-même, pour "envoie-moi un message..." — tiré de la
    liste blanche déjà configurée (WHATSAPP_ALLOWED_NUMBERS / TELEGRAM_ALLOWED_USER_IDS dans
    l'onglet Messagerie), qui contient normalement son propre numéro/ID puisque c'est la seule
    personne autorisée à échanger avec ARIA. Prend le premier de la liste. Ajouté le 12/09/2026."""
    raw = settings.WHATSAPP_ALLOWED_NUMBERS if channel == "whatsapp" else settings.TELEGRAM_ALLOWED_USER_IDS
    for candidate in raw.split(","):
        candidate = candidate.strip()
        if candidate:
            return candidate
    return None


async def _resolve_target(raw: str, channel: str) -> tuple[str | None, str]:
    """Renvoie (identifiant à utiliser, nom à afficher). Le premier est None si rien n'a pu être
    résolu (ni numéro valide, ni contact connu pour CE canal) — l'appelant doit alors renoncer et
    l'expliquer plutôt que d'envoyer/chercher n'importe quoi."""
    raw = _strip_channel_mentions(raw)
    if raw.strip(" ?.!\"'").lower() in {"moi", "moi-même", "moi même", "moi meme"}:
        return _own_identifier(channel), "toi"
    digits = _clean_number(raw)
    if channel == "whatsapp" and len(digits) >= 6:
        return digits, raw
    if channel == "telegram" and digits and digits == raw.strip():
        return digits, raw
    contact = await contacts_store.find_contact(raw)
    if contact and contact.get(channel):
        return contact[channel], contact["name"]
    return None, raw


async def _send(channel: str, to: str, text: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"http://{settings.API_HOST}:{settings.API_PORT}/api/{channel}/send",
                json={"to": to, "message": text},
            )
    except httpx.HTTPError as error:
        return f"Échec de l'envoi : {error}"
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", f"HTTP {response.status_code}")
        except ValueError:
            detail = f"HTTP {response.status_code}"
        return f"Échec de l'envoi : {detail}"
    return None  # succès signalé par l'appelant, avec le nom affiché plutôt que l'identifiant brut


async def _history(channel: str, contact_id: str | None) -> str:
    async with async_session() as session:
        query = select(Message).order_by(Message.created_at.desc()).limit(10)
        if contact_id:
            query = query.where(Message.conversation_id == f"{channel}:{contact_id}")
        else:
            query = query.where(Message.conversation_id.like(f"{channel}:%"))
        messages = (await session.execute(query)).scalars().all()
    return messages


def _channel_label(channel: str) -> str:
    return "WhatsApp" if channel == "whatsapp" else "Telegram"


async def _contacts_reply(channel: str | None) -> str:
    contacts = await contacts_store.list_contacts()
    if channel:
        contacts = [c for c in contacts if c.get(channel)]
    scope = f" {_channel_label(channel)}" if channel else ""
    if not contacts:
        return f"Aucun contact{scope} enregistré pour l'instant. Ajoute-en depuis l'onglet Messagerie."
    lines = []
    for contact in contacts:
        parts = []
        if contact.get("whatsapp"):
            parts.append(f"WhatsApp {contact['whatsapp']}")
        if contact.get("telegram"):
            parts.append(f"Telegram {contact['telegram']}")
        lines.append(f"{contact['name']} — {', '.join(parts)}")
    return f"Contacts{scope} enregistrés :\n" + "\n".join(lines)


async def handle(message: str, context: dict) -> dict:
    channel = _extract_channel(message)

    if WHATSAPP_OPEN_TRIGGER.match(message):
        return {
            "response": "J’ouvre le menu WhatsApp.",
            "data": {"navigate_to": "whatsapp"},
            "source": "local",
            "source_type": "whatsapp_open",
        }

    if _is_contacts(message):
        reply = await _contacts_reply(channel)
        return {"response": reply, "source": "local", "source_type": "messaging_contacts"}

    if _is_send(message):
        detail = SEND_DETAIL.search(message)
        if detail:
            target_raw, text = detail.group("to"), detail.group("text").strip()
        else:
            # Pas de SEND_DETAIL => c'est forcément SELF_SEND qui a matché (garanti par _is_send).
            target_raw = "moi"
            content_match = CONTENT_MARKER.search(message)
            text = content_match.group("text").strip() if content_match else None

        if text is None:
            reply = (
                f"Dis-moi ce que je dois envoyer sur {_channel_label(channel)} — par exemple : "
                f"« envoie-moi un message {channel} disant bien reçu »."
            )
            return {"response": reply, "source": "local", "source_type": "messaging_send"}

        target_id, display_name = await _resolve_target(target_raw, channel)
        if target_id is None:
            if target_raw == "moi":
                reply = (
                    f"Aucun numéro/identifiant {_channel_label(channel)} t'appartenant n'est "
                    "configuré. Renseigne-le dans les identifiants autorisés, onglet Messagerie."
                )
            else:
                reply = (
                    f"Je ne connais pas de contact {_channel_label(channel)} nommé « {display_name} ». "
                    "Ajoute-le dans l'onglet Messagerie (carnet de contacts), ou donne-moi directement "
                    "son numéro."
                )
        else:
            error = await _send(channel, target_id, text)
            reply = error or f"Message {_channel_label(channel)} envoyé à {display_name} : « {text} »"
        return {"response": reply, "source": "local", "source_type": "messaging_send"}

    # _is_history(message) — seul autre cas possible, garanti par matches() ci-dessus.
    contact_match = HISTORY_CONTACT.search(message) or HISTORY_QUESTION_CONTACT.search(message)
    contact_id, display_name = None, None
    if contact_match:
        contact_id, display_name = await _resolve_target(contact_match.group("contact"), channel)
        if contact_id is None:
            reply = (
                f"Je ne connais pas de contact {_channel_label(channel)} nommé « {display_name} ». "
                "Ajoute-le dans l'onglet Messagerie, ou donne-moi directement son numéro."
            )
            return {"response": reply, "source": "local", "source_type": "messaging_history"}

    messages = await _history(channel, contact_id)
    label = _channel_label(channel)
    if not messages:
        who = f" avec {display_name}" if display_name else ""
        reply = f"Aucun message {label}{who} pour l'instant."
    else:
        lines = [f"{'Toi' if m.role == 'user' else 'ARIA'} : {m.content}" for m in reversed(messages)]
        who = f" avec {display_name}" if display_name else ""
        reply = f"Derniers messages {label}{who} :\n" + "\n".join(lines)
    return {"response": reply, "source": "local", "source_type": "messaging_history"}
