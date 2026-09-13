"""Assistant fichiers dans le chat/vocal — permet à ARIA de naviguer, filtrer, rechercher, ouvrir
dans le visualiseur, analyser, créer, renommer et supprimer des fichiers/dossiers (dans FILES_ROOT
et les emplacements connus), depuis le Chat comme depuis l'Assistant vocal. Même schéma que
calendar/chat_handler.py (tool use natif Claude) — voir services/file_assistant.py.

Détection large volontairement (mots-clés fichiers/dossiers + un verbe d'action) : un faux positif
envoie juste la demande vers l'assistant fichiers, qui répond normalement si ce n'était pas une
vraie demande — beaucoup moins coûteux qu'un faux négatif qui ignorerait une vraie demande.

order=150 : après quiz(90)/kings(100), avant calendar(200) — les mots-clés fichiers/dossiers ne
recoupent pas ceux des autres handlers plus prioritaires."""
import re

from fastapi import HTTPException

from config import settings
from services import file_assistant
from services.claude_service import claude_service

_FILE_PATTERN = re.compile(
    r"\b(fichiers?|dossiers?|r[ée]pertoires?|documents?)\b[\s\S]{0,40}\b("
    r"ouvre|ouvrir|affiche|afficher|montre|montrer|liste|lister|cherche|chercher|trouve|trouver|"
    r"filtre|filtrer|renomme|renommer|cr[ée]e|cr[ée]er|supprime|supprimer|efface|effacer|"
    r"analyse|analyser|contenu"
    r")\b"
    r"|\b(ouvre|affiche|montre|cherche|trouve|filtre|renomme|cr[ée]e|supprime|efface|analyse)\b[\s\S]{0,40}"
    r"\b(fichiers?|dossiers?|r[ée]pertoires?|documents?)\b",
    re.IGNORECASE,
)


def matches(message: str) -> bool:
    return bool(message and _FILE_PATTERN.search(message))


async def handle(message: str, context: dict) -> dict:
    if claude_service.client is None:
        raise HTTPException(status_code=503, detail="Claude API is not configured")
    # SERVICE_ERRORS (httpx.HTTPError, LookupError, IndexError, KeyError, ValueError, TypeError)
    # levée par file_assistant.run() remonte telle quelle : le mécanisme générique de
    # plugin_loader la convertit en 502 avec le chat_error_message du manifest.
    response, nav = await file_assistant.run(message, claude_service.client, settings.CLAUDE_MODEL)
    result = {
        "response": response,
        "source": "ai",
        # "file_summary" quand un compte rendu de dossier a été demandé (summarize_directory) :
        # le frontend affiche alors une carte de stats structurée (DirectorySummaryCard) au lieu
        # du seul texte markdown — voir ChatComponent.jsx.
        "source_type": "file_summary" if nav.get("summary") else "file_assistant",
    }
    if nav:
        result["data"] = {"navigate_to": "files", **nav}
    return result
