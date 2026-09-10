"""File management service"""
import os
from pathlib import Path
from config import settings

class FileService:
    root = Path(settings.FILES_ROOT).expanduser().resolve()
    # Emplacements des dossiers spéciaux (Bureau, Documents...) : ne changent pas en cours de
    # session, calculés une seule fois plutôt qu'à chaque appel (voir _aliases_cache ci-dessous).
    _aliases_cache = None
    alias_labels = {
        "desktop": "Bureau",
        "documents": "Documents",
        "download": "Téléchargements",
        "downloads": "Téléchargements",
        "favoris": "Favoris",
        "favorites": "Favoris",
        "pictures": "Images",
        "videos": "Vidéos",
        "music": "Musique",
        "data": "Données système",
    }

    @classmethod
    def aliases(cls):
        # Mis en cache : Path.home()/ProgramData impliquent des appels disque, et cette méthode
        # était rappelée pour CHAQUE fichier listé (via relative_path, voir list_files) — sur un
        # dossier de quelques centaines d'éléments, ça faisait des milliers d'appels disque
        # inutiles rien que pour recalculer ces mêmes chemins fixes. Cause probable du chargement
        # lent constaté le 10/09/2026 sur l'onglet Fichiers.
        if cls._aliases_cache is not None:
            return cls._aliases_cache
        home = Path.home().resolve()
        program_data = Path(os.environ.get("ProgramData", home / "Data")).resolve()
        # Pas d'alias "users" -> home.parent : ça exposait TOUS les comptes Windows de la
        # machine (C:\Users entier), pas seulement le dossier de l'utilisateur courant.
        # Faille de sécurité corrigée le 10/09/2026, cf. audit du projet.
        cls._aliases_cache = {
            "desktop": home / "Desktop",
            "documents": home / "Documents",
            "download": home / "Downloads",
            "downloads": home / "Downloads",
            "favoris": home / "Favorites",
            "favorites": home / "Favorites",
            "pictures": home / "Pictures",
            "videos": home / "Videos",
            "music": home / "Music",
            "data": program_data,
        }
        return cls._aliases_cache

    @classmethod
    def _alias_path(cls, path: str):
        normalized = (path or ".").replace("\\", "/").strip("/")
        first, _, remainder = normalized.partition("/")
        alias = first.casefold()
        target = cls.aliases().get(alias)
        if target is None:
            return None
        return target / remainder if remainder else target

    @classmethod
    def resolve_path(cls, path: str = ".") -> Path:
        requested = cls._alias_path(path)
        if requested is None:
            requested = (cls.root / (path or ".")).resolve()
        else:
            requested = requested.resolve()

        allowed_roots = [cls.root, *cls.aliases().values()]
        if not any(requested == allowed or allowed in requested.parents for allowed in allowed_roots):
            raise ValueError("Path is outside FILES_ROOT")
        return requested

    @classmethod
    def relative_path(cls, path: Path) -> str:
        path = path.resolve()
        if path == cls.root:
            return "."
        matching_aliases = [
            (alias, target)
            for alias, target in cls.aliases().items()
            if path == target or target in path.parents
        ]
        if matching_aliases:
            alias, target = max(matching_aliases, key=lambda item: len(item[1].parts))
            # Path.relative_to(target).as_posix() vaut "." (pas "") quand path == target, donc
            # une chaîne non vide → toujours "vraie" en Python. Sans ce cas particulier, atteindre
            # la racine d'un alias (ex. juste "Documents") renvoyait "documents/." au lieu de
            # "documents" : remonter depuis "documents/." redemandait "documents", qui redonnait
            # "documents/." — un aller-retour qui donnait l'impression que "dossier parent" ne
            # faisait plus rien (bug constaté et corrigé le 10/09/2026).
            suffix = path.relative_to(target).as_posix()
            if suffix == ".":
                suffix = ""
            return f"{alias}/{suffix}" if suffix else alias
        relative = path.relative_to(cls.root)
        return relative.as_posix() or "."

    @classmethod
    def get_locations(cls):
        """alias_labels a des alias en double vers le même dossier réel ("download" ET
        "downloads" pointent tous deux vers home/Downloads, idem "favoris"/"favorites") —
        prévu pour accepter les deux orthographes en entrée, mais ça faisait apparaître deux
        boutons identiques ("Téléchargements" x2, "Favoris" x2) dans la barre d'emplacements.
        On déduplique ici sur le DOSSIER résolu (pas la chaîne d'alias), en gardant le premier
        alias rencontré pour chaque dossier — l'ordre de alias_labels fait foi."""
        locations = [{"name": "Accueil", "path": "."}]
        seen_dirs = set()
        for alias, label in cls.alias_labels.items():
            location = cls._alias_path(alias)
            if location is None or not location.is_dir():
                continue
            resolved = location.resolve()
            if resolved in seen_dirs:
                continue
            seen_dirs.add(resolved)
            locations.append({"name": label, "path": alias})
        return locations

    @staticmethod
    def list_files(path: str = "."):
        """List files in directory.

        Deux optimisations (lenteur constatée et corrigée le 10/09/2026) :
        - relative_path(item) était appelé pour CHAQUE élément listé, alors qu'il ne dépend que
          du DOSSIER courant (pas de l'élément) : un fichier "rapport.pdf" dans "documents/2024"
          a pour chemin relatif "documents/2024/rapport.pdf", trivialement déductible du chemin
          du dossier parent (déjà calculé une seule fois) + le nom du fichier — pas besoin de
          rappeler resolve()/aliases() par élément.
        - os.scandir() (via Path.iterdir()) remplacé par os.scandir() direct : chaque DirEntry
          garde en cache les infos (type, taille...) récupérées lors du listage du dossier -
          Path.iterdir() + .is_dir()/.stat() séparés refaisaient un appel disque par élément et
          par info, alors qu'un seul DirEntry.stat() suffit (bien plus net sous Windows, où
          FindFirstFile/FindNextFile renvoie déjà ces infos en un seul passage)."""
        try:
            resolved = FileService.resolve_path(path)
            parent_relative = FileService.relative_path(resolved)
            files = []
            with os.scandir(resolved) as entries:
                for entry in entries:
                    try:
                        is_directory = entry.is_dir()
                        size = 0 if is_directory else (entry.stat().st_size if entry.is_file() else 0)
                    except OSError:
                        continue
                    child_relative = entry.name if parent_relative == "." else f"{parent_relative}/{entry.name}"
                    files.append({
                        "name": entry.name,
                        "path": child_relative,
                        "is_dir": is_directory,
                        "size": size,
                    })
            return files
        except (FileNotFoundError, NotADirectoryError, PermissionError, ValueError):
            return []
    
    @staticmethod
    def search_files(pattern: str, path: str = "."):
        """Search files by pattern"""
        files = []
        try:
            for root, dirs, filenames in os.walk(FileService.resolve_path(path)):
                for filename in filenames:
                    if pattern.lower() in filename.lower():
                        files.append(os.path.join(root, filename))
                        if len(files) >= 100:
                            return files
        except (PermissionError, ValueError):
            pass
        return files

file_service = FileService()
