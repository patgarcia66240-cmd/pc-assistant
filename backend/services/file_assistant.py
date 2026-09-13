"""Assistant conversationnel pour le plugin Fichiers : afficher un document dans le visualiseur,
lister/filtrer un répertoire, trouver un fichier, l'analyser, le renommer, le créer, le supprimer —
en langage naturel, depuis le Chat comme depuis l'Assistant vocal (les deux passent par
POST /api/chat/, voir routes/chat.py).

Même schéma que calendar_assistant.py : tool use natif de l'API Claude (paramètre `tools`,
`stop_reason == "tool_use"`, blocs `tool_use`/`tool_result`). L'exécution réelle passe TOUJOURS par
FileService (vrai système de fichiers, restreint à FILES_ROOT + alias connus, voir
resolve_path) — jamais de données inventées.

Contrairement à calendar_assistant.run() qui ne renvoie qu'un texte, run() renvoie ici aussi un
dict "nav" (chemin courant, motif de recherche, fichier à ouvrir...) construit au fil des outils
appelés, pour que le chat_handler puisse déclencher une navigation vers l'onglet Fichiers
(mécanisme générique data.navigate_to, voir pluginNavigation.js et FileManager.jsx)."""
import fnmatch
import json

from config import settings
from services.file_service import file_service

_TOOLS = [
    {
        "name": "list_directory",
        "description": (
            "Liste le contenu direct (fichiers et dossiers, avec taille) d'UN répertoire, non "
            "récursif, avec un filtre optionnel de motif glob sur le nom (ex. *.csv, *.pdf). "
            "Utilise \".\" ou un alias connu (bureau, documents, telechargements, images...) "
            "pour path si l'utilisateur ne précise pas de chemin exact. Pour un compte rendu ou "
            "un résumé global d'un dossier (y compris ses sous-dossiers), utilise plutôt "
            "summarize_directory."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin relatif ou alias (défaut \".\")"},
                "pattern": {"type": "string", "description": "Motif glob optionnel, ex. *.csv"},
            },
        },
    },
    {
        "name": "summarize_directory",
        "description": (
            "Calcule des statistiques réelles sur un dossier ET tous ses sous-dossiers : nombre "
            "de fichiers, nombre de sous-dossiers, taille totale, répartition par type de fichier "
            "(extension), et les fichiers les plus volumineux. À utiliser pour \"fais-moi un "
            "compte rendu / résumé / analyse de ce dossier\", ou toute question portant sur "
            "l'ensemble d'un dossier plutôt qu'un fichier précis — plus fiable que list_directory "
            "pour ce genre de demande car il compte réellement, sans deviner."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin relatif ou alias (défaut \".\")"},
            },
        },
    },
    {
        "name": "find_file",
        "description": (
            "Recherche récursive de fichiers par motif de nom glob (ex. *.pdf, rapport*.docx) "
            "dans un répertoire et ses sous-dossiers. À utiliser pour \"trouve-moi le fichier "
            "...\" quand l'emplacement exact n'est pas connu."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Motif glob, ex. *.pdf"},
                "path": {"type": "string", "description": "Répertoire de départ (défaut \".\")"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Lit et analyse le contenu d'un fichier (texte, code, Markdown, JSON, Word, Excel, "
            "PowerPoint, base SQLite...) pour le résumer ou répondre à des questions dessus. "
            "Ne pas utiliser pour de simples images/audio/vidéo/PDF non structuré, dont le "
            "contenu n'est pas analysable textuellement — utilise open_in_viewer à la place."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Chemin du fichier"}},
            "required": ["path"],
        },
    },
    {
        "name": "open_in_viewer",
        "description": (
            "Ouvre un fichier dans le visualiseur de l'onglet Fichiers de l'interface. À utiliser "
            "quand l'utilisateur demande explicitement d'afficher/ouvrir/voir un document."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Chemin du fichier à ouvrir"}},
            "required": ["path"],
        },
    },
    {
        "name": "create_folder",
        "description": "Crée un nouveau dossier.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin complet du nouveau dossier, nom inclus"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "create_file",
        "description": "Crée un nouveau fichier texte, avec un contenu initial optionnel.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin complet du nouveau fichier, nom inclus"},
                "content": {"type": "string", "description": "Contenu texte initial (optionnel)"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "rename_file",
        "description": "Renomme un fichier ou un dossier existant (reste dans le même répertoire).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin actuel du fichier/dossier"},
                "new_name": {"type": "string", "description": "Nouveau nom seul, sans chemin"},
            },
            "required": ["path", "new_name"],
        },
    },
    {
        "name": "delete_file",
        "description": (
            "Supprime définitivement un fichier ou un dossier (et tout son contenu s'il s'agit "
            "d'un dossier). Irréversible — n'utilise cet outil qu'après avoir identifié le fichier "
            "exact (chemin précis, via list_directory ou find_file si besoin) et que la demande "
            "de suppression est claire ; en cas de doute sur l'élément visé, demande une "
            "précision au lieu d'appeler cet outil."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Chemin exact à supprimer"}},
            "required": ["path"],
        },
    },
]


class ToolInputError(Exception):
    """Arguments fournis par Claude invalides ou incomplets — renvoyé comme tool_result en erreur
    plutôt que de planter le tour de conversation, pour que Claude puisse se corriger."""


def _compact(value, max_chars: int = 3000, max_items: int = 200):
    """Réduit récursivement une preview de FileService.read_file_content pour tenir dans le
    contexte envoyé à Claude (documents Office/bases SQLite potentiellement volumineux) — tronque
    seulement les grosses chaînes et listes, garde toute la structure (noms de colonnes, feuilles,
    diapositives, nombre de lignes...) pour que Claude puisse quand même répondre correctement."""
    if isinstance(value, str):
        if len(value) > max_chars:
            return value[:max_chars] + "… (tronqué)"
        return value
    if isinstance(value, list):
        truncated = [_compact(item, max_chars, max_items) for item in value[:max_items]]
        if len(value) > max_items:
            truncated.append(f"… ({len(value) - max_items} éléments supplémentaires non affichés)")
        return truncated
    if isinstance(value, dict):
        return {key: _compact(val, max_chars, max_items) for key, val in value.items()}
    return value


_HOME_ALIASES = {"accueil", "racine", "home", "root"}


def _normalize_path(path):
    """« Accueil » est le raccourci affiché dans l'interface pour la racine des fichiers (path=".").
    Claude peut recevoir ce mot dans la demande de l'utilisateur et le renvoyer tel quel comme
    chemin : on le convertit ici vers "." pour que les outils le reconnaissent comme la racine
    plutôt que de chercher un dossier littéralement nommé "accueil"."""
    if not path:
        return path
    if path.strip().lower() in _HOME_ALIASES:
        return "."
    return path


async def _execute_tool(name: str, args: dict, nav: dict) -> dict:
    """Exécute réellement l'opération fichier correspondante via FileService (vrai système de
    fichiers) — nav est enrichi au passage avec de quoi construire un data.navigate_to côté
    chat_handler (chemin courant, motif, fichier à ouvrir)."""
    if name == "list_directory":
        path = _normalize_path(args.get("path")) or "."
        pattern = args.get("pattern")
        files = file_service.list_files(path)
        if pattern:
            files = [entry for entry in files if fnmatch.fnmatch(entry["name"].lower(), pattern.lower())]
        nav["path"] = file_service.relative_path(file_service.resolve_path(path))
        if pattern:
            nav["search"] = pattern
        return {"path": nav["path"], "count": len(files), "files": _compact(files)}

    if name == "summarize_directory":
        path = _normalize_path(args.get("path")) or "."
        summary = file_service.summarize_directory(path)
        nav["path"] = summary["path"]
        # Stats brutes transmises telles quelles au frontend (chat_handler.py) pour que le chat
        # affiche une vraie carte de compte rendu (grille de stats, répartition par extension,
        # fichiers les plus lourds) plutôt que le seul texte markdown généré par Claude.
        nav["summary"] = summary
        return summary

    if name == "find_file":
        pattern = args.get("pattern")
        if not pattern:
            raise ToolInputError("pattern est obligatoire.")
        path = _normalize_path(args.get("path")) or "."
        matches = file_service.find_files(pattern, path)
        return {"pattern": pattern, "count": len(matches), "matches": matches}

    if name == "read_file":
        path = _normalize_path(args.get("path"))
        if not path:
            raise ToolInputError("path est obligatoire.")
        data = file_service.read_file_content(path)
        return _compact(data)

    if name == "open_in_viewer":
        path = _normalize_path(args.get("path"))
        if not path:
            raise ToolInputError("path est obligatoire.")
        resolved = file_service.resolve_path(path)
        if not resolved.is_file():
            raise ToolInputError("Ce chemin ne correspond pas à un fichier existant.")
        relative = file_service.relative_path(resolved)
        nav["open_path"] = relative
        nav["path"] = file_service.relative_path(resolved.parent)
        return {"opened": True, "path": relative}

    if name == "create_folder":
        path = _normalize_path(args.get("path"))
        if not path:
            raise ToolInputError("path est obligatoire.")
        created = file_service.create_folder(path)
        nav["path"] = file_service.relative_path(created.parent)
        return {"created": True, "path": file_service.relative_path(created)}

    if name == "create_file":
        path = _normalize_path(args.get("path"))
        if not path:
            raise ToolInputError("path est obligatoire.")
        created = file_service.create_file(path, args.get("content") or "")
        nav["path"] = file_service.relative_path(created.parent)
        return {"created": True, "path": file_service.relative_path(created)}

    if name == "rename_file":
        path = _normalize_path(args.get("path"))
        new_name = args.get("new_name")
        if not path or not new_name:
            raise ToolInputError("path et new_name sont obligatoires.")
        renamed = file_service.rename_path(path, new_name)
        nav["path"] = file_service.relative_path(renamed.parent)
        return {"renamed": True, "path": file_service.relative_path(renamed)}

    if name == "delete_file":
        path = _normalize_path(args.get("path"))
        if not path:
            raise ToolInputError("path est obligatoire.")
        resolved = file_service.resolve_path(path)
        parent_relative = file_service.relative_path(resolved.parent)
        file_service.delete_path(path)
        nav["path"] = parent_relative
        return {"deleted": True, "path": path}

    raise ToolInputError(f"Outil inconnu : {name}")


def _system_prompt() -> str:
    return (
        f"Tu es {settings.ARIA_NAME}, assistante IA. Réponds en {settings.ARIA_LANGUAGE}.\n"
        "Tu as accès en lecture/écriture au VRAI système de fichiers de l'utilisatrice (restreint "
        "à son dossier de travail et aux emplacements connus comme Bureau/Documents/Téléchargements), "
        "via des outils réels : list_directory, summarize_directory, find_file, read_file, "
        "open_in_viewer, create_folder, create_file, rename_file, delete_file. « Accueil » est le nom "
        "affiché dans l'interface pour la racine du dossier de travail : quand l'utilisateur dit "
        "« accueil », « la racine » ou « le dossier principal », utilise path=\".\" (ou omets path). "
        "N'invente jamais un chemin, un nom de fichier ou un contenu : utilise toujours "
        "list_directory ou find_file pour vérifier avant de renommer, supprimer ou lire un fichier "
        "précis, et ne réponds jamais avec une information que tu n'as pas obtenue par un outil.\n"
        "Si l'utilisateur demande d'afficher/ouvrir/voir un document, utilise open_in_viewer (qui "
        "l'ouvre réellement dans l'interface) plutôt que de simplement décrire son contenu. Si "
        "plusieurs fichiers correspondent à une demande de suppression ou de renommage, ou si le "
        "fichier visé n'est pas identifiable de façon certaine, demande de préciser plutôt que de "
        "choisir au hasard — delete_file est irréversible.\n"
        "Réponses concises et naturelles, adaptées à une lecture à voix haute. Tu peux utiliser "
        "**gras** (markdown) pour mettre en valeur un nom de fichier ou de dossier clé : "
        "l'interface l'affiche en gras réel."
    )


async def run(message: str, claude_client, model: str, max_rounds: int = 5):
    """Boucle de conversation avec tool use, jusqu'à une réponse texte finale ou max_rounds
    allers-retours (garde-fou : l'API Claude n'impose elle-même aucune limite). Renvoie
    (texte_reponse, nav) — nav est un dict vide si aucune navigation n'est pertinente."""
    messages = [{"role": "user", "content": message}]
    nav: dict = {}
    for _ in range(max_rounds):
        response = await claude_client.messages.create(
            model=model,
            max_tokens=1200,
            system=_system_prompt(),
            tools=_TOOLS,
            messages=messages,
        )
        if response.stop_reason != "tool_use":
            text = "".join(block.text for block in response.content if block.type == "text")
            return text or "D'accord.", nav

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                result = await _execute_tool(block.name, block.input, nav)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result, ensure_ascii=False)}
                )
            except ToolInputError as error:
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": str(error), "is_error": True}
                )
            except (FileNotFoundError, FileExistsError, ValueError, PermissionError, OSError) as error:
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": str(error), "is_error": True}
                )
        messages.append({"role": "user", "content": tool_results})

    return (
        "Je n'arrive pas à terminer cette action sur tes fichiers (trop d'étapes) — reformule ta demande plus précisément.",
        nav,
    )
