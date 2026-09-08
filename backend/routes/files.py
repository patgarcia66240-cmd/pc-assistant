"""File management routes"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/list")
async def list_files(path: str = "/"):
    """List files in directory"""
    return {"path": path, "files": []}

@router.post("/upload")
async def upload_file():
    """Upload a file"""
    return {"status": "uploaded"}
