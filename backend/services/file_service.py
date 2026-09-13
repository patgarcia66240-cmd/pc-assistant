"""File management service"""
import os
from pathlib import Path
from config import settings

# Limites de sécurité pour l'extraction de documents Office : évite de charger en mémoire
# (ou de renvoyer au frontend) des documents gigantesques (tableur de 100k lignes, etc.).
OFFICE_MAX_PARAGRAPHS = 2000
OFFICE_MAX_TABLE_ROWS = 200
OFFICE_MAX_SHEET_ROWS = 500
OFFICE_MAX_SHEET_COLS = 50
OFFICE_MAX_SLIDES = 300

# Limites de sécurité pour l'aperçu des bases de données SQLite.
DB_MAX_TABLES = 100
DB_MAX_ROWS_PER_TABLE = 200

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
    def read_file_content(path: str, max_text_bytes: int = 1024 * 1024):
        """Read file content or return metadata for preview.
        
        If it's text/code/markdown/json, returns UTF-8 text content (up to max_text_bytes).
        For binary or other formats, provides type classification and preview hints.
        """
        resolved = FileService.resolve_path(path)
        if not resolved.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        size = resolved.stat().st_size
        filename = resolved.name
        suffix = resolved.suffix.lower()

        # Classification des types
        text_extensions = {
            ".txt", ".md", ".json", ".js", ".jsx", ".ts", ".tsx", ".py", ".html",
            ".css", ".scss", ".xml", ".yaml", ".yml", ".ini", ".cfg", ".conf",
            ".sh", ".bat", ".ps1", ".sql", ".env", ".log", ".csv", ".toml", ".rs",
            ".c", ".cpp", ".h", ".hpp", ".java", ".go", ".cs"
        }
        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"}
        audio_extensions = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"}
        video_extensions = {".mp4", ".webm", ".mkv", ".mov", ".avi"}
        pdf_extensions = {".pdf"}
        docx_extensions = {".docx"}
        xlsx_extensions = {".xlsx", ".xlsm"}
        pptx_extensions = {".pptx"}
        db_extensions = {".db", ".sqlite", ".sqlite3", ".db3"}

        if suffix in image_extensions:
            file_type = "image"
        elif suffix in audio_extensions:
            file_type = "audio"
        elif suffix in video_extensions:
            file_type = "video"
        elif suffix in pdf_extensions:
            file_type = "pdf"
        elif suffix in docx_extensions:
            file_type = "docx"
        elif suffix in xlsx_extensions:
            file_type = "xlsx"
        elif suffix in pptx_extensions:
            file_type = "pptx"
        elif suffix in db_extensions:
            file_type = "db"
        elif suffix in text_extensions:
            file_type = "text"
        else:
            file_type = "binary"

        result = {
            "name": filename,
            "path": FileService.relative_path(resolved),
            "size": size,
            "type": file_type,
            "extension": suffix,
            "truncated": False,
            "content": None
        }

        if file_type == "docx":
            document = FileService._extract_docx(resolved)
            if document is not None:
                result["document"] = document
            else:
                # Fichier corrompu/protégé : on retombe sur le téléchargement seul.
                result["type"] = "binary"
            return result

        if file_type == "xlsx":
            workbook = FileService._extract_xlsx(resolved)
            if workbook is not None:
                result["workbook"] = workbook
            else:
                result["type"] = "binary"
            return result

        if file_type == "pptx":
            presentation = FileService._extract_pptx(resolved)
            if presentation is not None:
                result["presentation"] = presentation
            else:
                result["type"] = "binary"
            return result

        if file_type == "db":
            database = FileService._extract_sqlite(resolved)
            if database is not None:
                result["database"] = database
            else:
                result["type"] = "binary"
            return result

        # Tentative de lecture en texte si le type est text ou non déterminé
        if file_type == "text" or (file_type == "binary" and size <= max_text_bytes):
            try:
                # Lire jusqu'à max_text_bytes
                with open(resolved, "rb") as f:
                    raw = f.read(max_text_bytes + 1)
                
                is_truncated = len(raw) > max_text_bytes
                if is_truncated:
                    raw = raw[:max_text_bytes]
                
                # Décodage UTF-8 (ou latin1 en fallback si petit fichier texte)
                try:
                    text_content = raw.decode("utf-8")
                    result["content"] = text_content
                    result["truncated"] = is_truncated
                    result["type"] = "text"
                except UnicodeDecodeError:
                    if file_type != "text":
                        result["type"] = "binary"
                    else:
                        result["content"] = raw.decode("latin1", errors="replace")
                        result["truncated"] = is_truncated
            except Exception:
                pass

        return result

    @staticmethod
    def _extract_docx(resolved: Path):
        """Extrait paragraphes (avec style) et tableaux d'un document Word."""
        try:
            from docx import Document
        except ImportError:
            return None
        try:
            doc = Document(str(resolved))
        except Exception:
            return None

        paragraphs = []
        truncated = False
        for para in doc.paragraphs:
            if len(paragraphs) >= OFFICE_MAX_PARAGRAPHS:
                truncated = True
                break
            text = para.text
            if text.strip() == "":
                continue
            style_name = (para.style.name if para.style else "") or ""
            is_heading = style_name.lower().startswith("heading")
            heading_level = 0
            if is_heading:
                try:
                    heading_level = int(style_name.split(" ")[-1])
                except ValueError:
                    heading_level = 1
            is_list = "list" in style_name.lower()
            paragraphs.append({
                "text": text,
                "heading": heading_level,
                "list": is_list,
                "bold": any(run.bold for run in para.runs) if para.runs else False,
                "italic": any(run.italic for run in para.runs) if para.runs else False,
            })

        tables = []
        for table in doc.tables:
            rows = []
            for row in table.rows[:OFFICE_MAX_TABLE_ROWS]:
                rows.append([cell.text for cell in row.cells])
            tables.append({"rows": rows, "truncated": len(table.rows) > OFFICE_MAX_TABLE_ROWS})

        return {"paragraphs": paragraphs, "tables": tables, "truncated": truncated}

    @staticmethod
    def _extract_xlsx(resolved: Path):
        """Extrait les feuilles (grille de cellules) d'un classeur Excel."""
        try:
            from openpyxl import load_workbook
        except ImportError:
            return None
        try:
            wb = load_workbook(str(resolved), read_only=True, data_only=True)
        except Exception:
            return None

        sheets = []
        try:
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = []
                row_truncated = False
                col_truncated = False
                for row_index, row in enumerate(ws.iter_rows(values_only=True)):
                    if row_index >= OFFICE_MAX_SHEET_ROWS:
                        row_truncated = True
                        break
                    values = list(row)
                    if len(values) > OFFICE_MAX_SHEET_COLS:
                        col_truncated = True
                        values = values[:OFFICE_MAX_SHEET_COLS]
                    rows.append(["" if v is None else str(v) for v in values])
                sheets.append({
                    "name": sheet_name,
                    "rows": rows,
                    "truncated": row_truncated or col_truncated,
                })
        finally:
            wb.close()

        return {"sheets": sheets}

    @staticmethod
    def _extract_pptx(resolved: Path):
        """Extrait le texte de chaque diapositive d'une présentation PowerPoint."""
        try:
            from pptx import Presentation
        except ImportError:
            return None
        try:
            prs = Presentation(str(resolved))
        except Exception:
            return None

        slides = []
        truncated = False
        for index, slide in enumerate(prs.slides):
            if index >= OFFICE_MAX_SLIDES:
                truncated = True
                break
            title = ""
            texts = []
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                shape_text = "\n".join(
                    p.text for p in shape.text_frame.paragraphs if p.text.strip() != ""
                )
                if shape_text.strip() == "":
                    continue
                if shape == slide.shapes.title:
                    title = shape_text
                else:
                    texts.append(shape_text)
            notes = ""
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes = slide.notes_slide.notes_text_frame.text
            slides.append({
                "index": index + 1,
                "title": title,
                "texts": texts,
                "notes": notes,
            })

        return {"slides": slides, "truncated": truncated}

    @staticmethod
    def _extract_sqlite(resolved: Path):
        """Extrait la structure (tables, colonnes) et un aperçu des lignes d'une base SQLite."""
        import sqlite3

        # Un fichier SQLite valide commence toujours par cet en-tête de 16 octets.
        try:
            with open(resolved, "rb") as f:
                header = f.read(16)
        except Exception:
            return None
        if header != b"SQLite format 3\x00":
            return None

        try:
            # mode=ro : ouverture en lecture seule, ne modifie jamais le fichier source.
            conn = sqlite3.connect(f"file:{resolved.as_posix()}?mode=ro", uri=True)
        except Exception:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            table_names = [row[0] for row in cursor.fetchall()]

            tables = []
            truncated_tables = len(table_names) > DB_MAX_TABLES
            for table_name in table_names[:DB_MAX_TABLES]:
                safe_name = table_name.replace('"', '""')
                cursor.execute(f'PRAGMA table_info("{safe_name}")')
                columns = [col[1] for col in cursor.fetchall()]

                try:
                    cursor.execute(f'SELECT COUNT(*) FROM "{safe_name}"')
                    row_count = cursor.fetchone()[0]
                except Exception:
                    row_count = 0

                try:
                    cursor.execute(f'SELECT * FROM "{safe_name}" LIMIT {DB_MAX_ROWS_PER_TABLE}')
                    rows = [
                        ["" if value is None else str(value) for value in row]
                        for row in cursor.fetchall()
                    ]
                except Exception:
                    rows = []

                tables.append({
                    "name": table_name,
                    "columns": columns,
                    "rows": rows,
                    "row_count": row_count,
                    "truncated": row_count > DB_MAX_ROWS_PER_TABLE,
                })

            return {"tables": tables, "truncated": truncated_tables}
        except Exception:
            return None
        finally:
            conn.close()

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
