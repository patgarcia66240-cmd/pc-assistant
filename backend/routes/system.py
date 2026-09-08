"""System monitoring routes"""
from fastapi import APIRouter
from services.system_service import system_service

router = APIRouter()

@router.get("/info")
async def get_system_info():
    """Get system information"""
    return system_service.get_system_info()

@router.get("/processes")
async def get_processes():
    """Get running processes."""
    return {"processes": system_service.get_processes()}
