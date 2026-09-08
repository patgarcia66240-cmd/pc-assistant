"""System monitoring routes"""
from fastapi import APIRouter
import psutil

router = APIRouter()

@router.get("/info")
async def get_system_info():
    """Get system information"""
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory": psutil.virtual_memory()._asdict(),
        "disk": psutil.disk_usage("/")._asdict()
    }

@router.get("/processes")
async def get_processes():
    """Get running processes"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        processes.append(proc.info)
    return {"processes": processes[:20]}
