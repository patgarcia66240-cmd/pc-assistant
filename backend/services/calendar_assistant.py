"""Assistant conversationnel pour Google Agenda : consulter, ajouter, modifier, supprimer et
filtrer des événements en langage naturel, depuis le Chat comme depuis l'Assistant vocal (les deux
passent par POST /api/chat/, voir routes/chat.py).

Utilise le tool use natif de l'API Claude (vérifié le 10/09/2026 sur platform.claude.com/docs —
paramètre `tools` avec `name`/`description`/`input_schema`, `stop_reason == "tool_use"`, blocs
`tool_use`/`tool_result`) : Claude décide quels outils appeler et avec quels arguments, mais
l'exécution réelle passe TOUJOURS par google_calendar_service (vrais appels à l'API Google
Calendar) — jamais de données inventées, conformément au reste du backend (kings_service,
city_info_service...) qui sert des faits réels plutôt que de laisser l'IA générative deviner.
"""
import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from config import settings
from services import google_calendar_service as gcal

# Fuseau horaire de l'utilisatrice — Saint-Martin-de-Crau, France (voir USER_CITY_LABEL dans
# config.py) : la France entière est sur Europe/Paris, pas besoin d'une conversion plus fine.
_TIMEZONE = "Europe/Paris"

# Détection large volontairement : un faux positif envoie juste la demande vers l'assistant
# agenda, qui a le choix de ne PAS appeler d'outil et de répondre normalement si ce n'était pas
# une vraie demande d'agenda — beaucoup moins coûteux qu'un faux négatif qui ignorerait une vraie
# demande de rendez-vous.
_CALENDAR_PATTERN = re.compile(r"\b(rendez[- ]vous|rdv|agenda|calendrier)\b", re.IGNORECASE)


def is_calendar_request(message: str) -> bool:
    return bool(_CALENDAR_PATTERN.search(message))


_TOOLS = [
    {
        "name": "list_events",
        "description": (
            "Liste les événements du Google Agenda connecté entre deux instants RFC3339. À "
            "utiliser pour consulter, chercher, filtrer l'agenda, ou pour retrouver l'event_id "
            "exact d'un événement avant de le modifier ou le supprimer — ne jamais deviner un "
            "event_id, toujours le récupérer via cet outil d'abord."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "time_min": {
                    "type": "string",
                    "description": "Début de la période, RFC3339 avec fuseau (ex. 2026-09-10T00:00:00+02:00)",
                },
                "time_max": {
                    "type": "string",
                    "description": "Fin de la période, RFC3339 avec fuseau",
                },
            },
            "required": ["time_min", "time_max"],
        },
    },
    {
        "name": "create_event",
        "description": "Crée un nouvel événement réel dans le Google Agenda connecté.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Titre de l'événement"},
                "description": {"type": "string", "description": "Description optionnelle"},
                "location": {"type": "string", "description": "Lieu optionnel"},
                "all_day": {"type": "boolean", "description": "true si l'événement dure toute la journée"},
                "date": {"type": "string", "description": "Date au format YYYY-MM-DD"},
                "start_time": {"type": "string", "description": "Heure de début HH:MM (obligatoire si all_day=false)"},
                "end_time": {"type": "string", "description": "Heure de fin HH:MM (obligatoire si all_day=false)"},
            },
            "required": ["summary", "all_day", "date"],
        },
    },
    {
        "name": "update_event",
        "description": (
            "Modifie un événement existant. Fournis TOUJOURS l'ensemble des champs à jour "
            "(titre, date, heures...), pas seulement celui qui change — récupère d'abord "
            "l'événement complet via list_events pour ne pas perdre les autres champs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Identifiant exact de l'événement (obtenu via list_events)"},
                "calendar_id": {
                    "type": "string",
                    "description": "Agenda contenant l'événement — champ calendar_id renvoyé par list_events pour ce même événement, jamais deviné.",
                },
                "summary": {"type": "string"},
                "description": {"type": "string"},
                "location": {"type": "string"},
                "all_day": {"type": "boolean"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "start_time": {"type": "string", "description": "HH:MM (obligatoire si all_day=false)"},
                "end_time": {"type": "string", "description": "HH:MM (obligatoire si all_day=false)"},
            },
            "required": ["event_id", "calendar_id", "summary", "all_day", "date"],
        },
    },
    {
        "name": "delete_event",
        "description": "Supprime définitivement un événement du Google Agenda connecté.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Identifiant exact de l'événement (obtenu via list_events)"},
                "calendar_id": {
                    "type": "string",
                    "description": "Agenda contenant l'événement — champ calendar_id renvoyé par list_events pour ce même événement, jamais deviné.",
                },
            },
            "required": ["event_id", "calendar_id"],
        },
    },
]


class ToolInputError(Exception):
    """Arguments fournis par Claude invalides ou incomplets — renvoyé comme tool_result en erreur
    plutôt que de planter le tour de conversation, pour que Claude puisse se corriger."""


def _build_payload(args: dict) -> dict:
    """Construit le payload attendu par l'API Calendar — mêmes règles que buildEventPayload dans
    CalendarAgenda.jsx (end.date exclusif pour les événements toute la journée), pour que
    l'assistant conversationnel et la grille produisent des événements identiques."""
    summary = (args.get("summary") or "").strip()
    if not summary:
        raise ToolInputError("Le titre (summary) est obligatoire.")
    payload = {"summary": summary}
    if args.get("description"):
        payload["description"] = args["description"]
    if args.get("location"):
        payload["location"] = args["location"]

    date_str = args.get("date")
    if not date_str:
        raise ToolInputError("La date (date, format YYYY-MM-DD) est obligatoire.")
    try:
        year, month, day = (int(part) for part in date_str.split("-"))
        base_date = datetime(year, month, day)
    except (ValueError, TypeError) as error:
        raise ToolInputError(f"Date invalide ({date_str!r}), attendu YYYY-MM-DD.") from error

    if args.get("all_day"):
        end_date = base_date + timedelta(days=1)
        payload["start"] = {"date": date_str}
        payload["end"] = {"date": end_date.strftime("%Y-%m-%d")}
        return payload

    start_time = args.get("start_time")
    end_time = args.get("end_time")
    if not start_time or not end_time:
        raise ToolInputError("start_time et end_time (HH:MM) sont obligatoires quand all_day=false.")
    payload["start"] = {"dateTime": f"{date_str}T{start_time}:00", "timeZone": _TIMEZONE}
    payload["end"] = {"dateTime": f"{date_str}T{end_time}:00", "timeZone": _TIMEZONE}
    return payload


async def _execute_tool(name: str, args: dict) -> dict:
    """Exécute réellement l'appel Google Calendar correspondant — jamais de simulation, jamais de
    réponse fabriquée : soit l'appel réel réussit, soit l'erreur réelle remonte à Claude."""
    if name == "list_events":
        time_min = args.get("time_min")
        time_max = args.get("time_max")
        if not time_min or not time_max:
            raise ToolInputError("time_min et time_max (RFC3339) sont obligatoires.")
        events = await gcal.list_events(time_min, time_max)
        # Champs utiles à Claude uniquement, pour économiser du contexte sur un agenda chargé.
        # calendar_id : nécessaire pour qu'un update_event/delete_event ultérieur cible le bon
        # agenda (list_events agrège désormais tous les agendas visibles du compte, pas
        # seulement l'agenda principal — voir google_calendar_service.list_events).
        return {
            "events": [
                {
                    "id": event.get("id"),
                    "calendar_id": event.get("calendarId"),
                    "summary": event.get("summary"),
                    "start": event.get("start"),
                    "end": event.get("end"),
                    "location": event.get("location"),
                    "description": event.get("description"),
                }
                for event in events
            ]
        }
    if name == "create_event":
        created = await gcal.create_event(_build_payload(args))
        return {"created": True, "event_id": created.get("id"), "htmlLink": created.get("htmlLink")}
    if name == "update_event":
        event_id = args.get("event_id")
        calendar_id = args.get("calendar_id")
        if not event_id or not calendar_id:
            raise ToolInputError("event_id et calendar_id sont obligatoires (récupérés via list_events).")
        updated = await gcal.update_event(event_id, _build_payload(args), calendar_id)
        return {"updated": True, "event_id": updated.get("id")}
    if name == "delete_event":
        event_id = args.get("event_id")
        calendar_id = args.get("calendar_id")
        if not event_id or not calendar_id:
            raise ToolInputError("event_id et calendar_id sont obligatoires (récupérés via list_events).")
        await gcal.delete_event(event_id, calendar_id)
        return {"deleted": True, "event_id": event_id}
    raise ToolInputError(f"Outil inconnu : {name}")


def _system_prompt() -> str:
    try:
        now = datetime.now(ZoneInfo(_TIMEZONE))
    except ZoneInfoNotFoundError:
        # Windows sans le paquet tzdata (voir requirements.txt) : plutôt qu'un 500 sur tout
        # l'assistant agenda, on se rabat sur l'heure système locale (déjà celle de l'utilisatrice
        # en pratique, juste sans nom de fuseau explicite pour Claude).
        now = datetime.now()
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    return (
        f"Tu es {settings.ARIA_NAME}, assistante IA. Réponds en {settings.ARIA_LANGUAGE}.\n"
        f"Nous sommes le {jours[now.weekday()]} {now.strftime('%d/%m/%Y')}, il est {now.strftime('%H:%M')} "
        f"(heure de {settings.USER_CITY_LABEL}, fuseau {_TIMEZONE}).\n"
        "Tu as accès en lecture/écriture au VRAI Google Agenda connecté, via des outils réels. "
        "N'invente jamais un événement, une date ou un identifiant : utilise toujours list_events "
        "pour vérifier avant de modifier ou supprimer, et ne réponds jamais avec une information "
        "que tu n'as pas obtenue par un outil. Si plusieurs événements correspondent à une demande "
        "de modification ou de suppression, demande de préciser plutôt que de choisir au hasard. "
        "Réponses concises et naturelles, adaptées à une lecture à voix haute. Tu peux utiliser "
        "**gras** (markdown) pour mettre en valeur une information clé (date, heure, nom) : "
        "l'interface l'affiche en gras réel, et respecte aussi les retours à la ligne que tu "
        "écris (\\n) — l'interface les affiche tels quels.\n"
        "Quand ta réponse liste PLUSIEURS rendez-vous ou événements, mets-en UN PAR LIGNE (un "
        "vrai retour à la ligne entre chaque, jamais enchaînés dans la même phrase), au format : "
        "**jour date** - heure début-heure fin : titre (lieu si connu). Si tu ajoutes une phrase "
        "d'introduction ou de résumé, mets-la sur sa propre ligne, séparée de la liste par une "
        "ligne vide."
    )


async def run(message: str, claude_client, model: str, max_rounds: int = 5) -> str:
    """Boucle de conversation avec tool use, jusqu'à une réponse texte finale ou max_rounds
    allers-retours (garde-fou : l'API Claude n'impose elle-même aucune limite, voir doc vérifiée)."""
    messages = [{"role": "user", "content": message}]
    for _ in range(max_rounds):
        response = await claude_client.messages.create(
            model=model,
            max_tokens=1024,
            system=_system_prompt(),
            tools=_TOOLS,
            messages=messages,
        )
        if response.stop_reason != "tool_use":
            text = "".join(block.text for block in response.content if block.type == "text")
            return text or "D'accord."

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                result = await _execute_tool(block.name, block.input)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result, ensure_ascii=False)}
                )
            except ToolInputError as error:
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": str(error), "is_error": True}
                )
            except gcal.CalendarNotConnectedError:
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": "Google Agenda non connecté.", "is_error": True}
                )
            except Exception as error:  # y compris httpx.HTTPStatusError (erreur Google réelle)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": str(error), "is_error": True}
                )
        messages.append({"role": "user", "content": tool_results})

    return "Je n'arrive pas à terminer cette action sur ton agenda (trop d'étapes) — reformule ta demande plus précisément."
