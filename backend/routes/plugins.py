"""Routes de gestion des plugins ARIA (liste + activation/désactivation)."""
from fastapi import APIRouter, HTTPException

from plugin_loader import list_plugin_status, set_plugin_enabled

router = APIRouter()


@router.get("")
async def get_plugins():
    """Liste tous les plugins découverts avec leur état actuel (activé ou non)."""
    return list_plugin_status()


@router.post("/{plugin_id}/enable")
async def enable_plugin(plugin_id: str):
    try:
        return set_plugin_enabled(plugin_id, True)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' introuvable")


@router.post("/{plugin_id}/disable")
async def disable_plugin(plugin_id: str):
    try:
        return set_plugin_enabled(plugin_id, False)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' introuvable")
