"""File management routes"""
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, UploadFile
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
