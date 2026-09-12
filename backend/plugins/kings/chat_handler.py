"""Handler de chat pour les rois de France — extrait de routes/chat.py le 11/09/2026, comme
premier exemple du mécanisme de "chat handler" en plugin (voir plugin_loader.get_chat_handlers).
Fiches servies depuis SQLite (data/kings.db), jamais par l'IA générative (demande explicite :
ne pas appeler l'IA pour rien pour ces faits)."""
from services.kings_service import get_king_answer, is_king_request

matches = is_king_request


async def handle(message: str, context: dict) -> dict:
    # Une seule fonction gère requête vide / roi non trouvé / plusieurs rois ambigus / roi
    # trouvé (voir kings_service.get_king_answer) — pas besoin d'un attrape-tout séparé comme
    # pour bourse/cours, il n'y a qu'une seule sous-catégorie ici.
    response = await get_king_answer(message)
    # data : soit une fiche de roi précis ("king", objet), soit une liste ("kings_list",
    # tableau — liste complète ou désambiguïsation) pour que le frontend affiche une frise
    # chronologique plutôt qu'un mur de texte (demande explicite de l'utilisatrice).
    return {
        "response": response["text"],
        "data": response.get("king") if response.get("king") is not None else response.get("kings_list"),
        "source": "local",
        "source_type": "king",
    }
