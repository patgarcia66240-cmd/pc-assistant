"""File management routes"""
from pathlib import Path
from fastapi import APIRouter, Body, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from services.file_service import file_service

router = APIRouter()

# Erreurs métier de FileService (chemin invalide, existe déjà, introuvable, racine protégée...)
# converties en 4xx explicites plutôt qu'un 500 générique — mêmes exceptions que celles
# attrapées par l'assistant fichiers du chat (voir services/file_assistant.py).
_CREATE_CONFLICT_ERRORS = (FileExistsError,)
_NOT_FOUND_ERRORS = (FileNotFoundError,)
_BAD_REQUEST_ERRORS = (ValueError,)

@router.get("/locations")
async def list_locations():
    """Return common Windows locations inside FILES_ROOT."""
    return {"locations": file_service.get_locations()}

@router.get("/list")
async def list_files(path: str = "."):
    """List files in directory"""
    try:
        files = file_service.list_files(path)
        current_path = file_service.relative_path(file_service.resolve_path(path))
    except Exception as error:
        raise HTTPException(status_code=400, detail="Invalid path") from error
    return {"path": current_path, "files": files}

@router.get("/content")
async def get_file_content(path: str):
    """Get metadata and text content (if applicable) of a file."""
    try:
        return file_service.read_file_content(path)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="File not found") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid path") from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

@router.get("/raw")
async def get_file_raw(path: str, download: bool = False):
    """Serve the raw file stream for images, audio, video, PDF or download."""
    try:
        resolved = file_service.resolve_path(path)
        if not resolved.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Déterminer si on force le téléchargement
        filename = resolved.name
        headers = {}
        if download:
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'
            
        return FileResponse(
            path=str(resolved),
            filename=filename if download else None,
            headers=headers
        )
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid path") from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file"""
    filename = Path(file.filename or "").name
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    destination = file_service.resolve_path(filename)
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                output.write(chunk)
    except OSError as error:
        raise HTTPException(status_code=500, detail="Could not save file") from error
    finally:
        await file.close()

    return {"status": "uploaded", "name": filename}

@router.get("/search")
async def find_files(pattern: str, path: str = "."):
    """Recherche récursive par motif glob (ex. *.pdf) — utilisé par le filtre glob de l'UI ET
    par l'assistant fichiers du chat pour "trouve-moi le fichier ..."."""
    try:
        matches = file_service.find_files(pattern, path)
    except _BAD_REQUEST_ERRORS as error:
        raise HTTPException(status_code=400, detail="Invalid path") from error
    return {"pattern": pattern, "matches": matches}

@router.get("/summary")
async def summarize_directory(path: str = "."):
    """Statistiques récursives d'un dossier (nombre de fichiers/dossiers, taille totale,
    répartition par extension, plus gros fichiers) — utilisé par l'assistant fichiers du chat
    pour produire un vrai compte rendu plutôt qu'une simple liste."""
    try:
        return file_service.summarize_directory(path)
    except NotADirectoryError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except _BAD_REQUEST_ERRORS as error:
        raise HTTPException(status_code=400, detail="Invalid path") from error

@router.post("/folder")
async def create_folder(path: str = Body(..., embed=True)):
    """Create a new folder"""
    try:
        created = file_service.create_folder(path)
    except _CREATE_CONFLICT_ERRORS as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except _BAD_REQUEST_ERRORS as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except OSError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    return {"status": "created", "path": file_service.relative_path(created)}

@router.post("/file")
async def create_file(path: str = Body(..., embed=True), content: str = Body("", embed=True)):
    """Create a new text file"""
    try:
        created = file_service.create_file(path, content)
    except _CREATE_CONFLICT_ERRORS as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except _BAD_REQUEST_ERRORS as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except OSError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    return {"status": "created", "path": file_service.relative_path(created)}

@router.post("/rename")
async def rename_path(path: str = Body(..., embed=True), new_name: str = Body(..., embed=True)):
    """Rename a file or folder (stays in the same parent directory)"""
    try:
        renamed = file_service.rename_path(path, new_name)
    except _NOT_FOUND_ERRORS as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except _CREATE_CONFLICT_ERRORS as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except _BAD_REQUEST_ERRORS as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except OSError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    return {"status": "renamed", "path": file_service.relative_path(renamed)}

@router.delete("/delete")
async def delete_path(path: str):
    """Delete a file or a folder (and all its content)"""
    try:
        file_service.delete_path(path)
    except _NOT_FOUND_ERRORS as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except _BAD_REQUEST_ERRORS as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except OSError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    return {"status": "deleted", "path": path}
