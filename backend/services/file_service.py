"""File management service"""
import os
from pathlib import Path
from config import settings

class FileService:
    root = Path(settings.FILES_ROOT).expanduser().resolve()
    alias_labels = {
        "users": "Utilisateurs",
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
        home = Path.home().resolve()
        program_data = Path(os.environ.get("ProgramData", home / "Data")).resolve()
        return {
            "users": home.parent,
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
            suffix = path.relative_to(target).as_posix()
            return f"{alias}/{suffix}" if suffix else alias
        relative = path.relative_to(cls.root)
        return relative.as_posix() or "."

    @classmethod
    def get_locations(cls):
        locations = [{"name": "Accueil", "path": "."}]
        for alias, label in cls.alias_labels.items():
            location = cls._alias_path(alias)
            if location.is_dir() and not any(item["path"] == alias for item in locations):
                locations.append({"name": label, "path": alias})
        return locations

    @staticmethod
    def list_files(path: str = "."):
        """List files in directory"""
        try:
            files = []
            for item in FileService.resolve_path(path).iterdir():
                files.append({
                    "name": item.name,
                    "path": FileService.relative_path(item),
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0
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
