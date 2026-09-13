"""File management routes"""
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from services.file_service import file_service

router = APIRouter()

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
