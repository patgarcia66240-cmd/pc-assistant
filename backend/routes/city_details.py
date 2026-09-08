"""Complementary, heavier city data (housing price, cost-of-living budget) — fetched on demand."""
from fastapi import APIRouter, HTTPException
from services.city_info_service import get_city_details_status, fetch_city_details, delete_city_info

router = APIRouter()


@router.get("/{city}/status")
async def city_details_status(city: str):
    """Lecture pure du cache (aucun appel réseau) : dit si des détails existent déjà,
    pour que le frontend propose une confirmation avant de les actualiser."""
    return await get_city_details_status(city)


@router.post("/{city}/refresh")
async def city_details_refresh(city: str):
    """Relance les API complémentaires (DVF, etc.) et écrase le cache avec le résultat."""
    try:
        return await fetch_city_details(city)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/{city}")
async def city_info_delete(city: str):
    """Supprime entièrement la fiche d'une ville (cache mémoire + ligne SQLite)."""
    deleted = await delete_city_info(city)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Aucune fiche en cache pour: {city}")
    return {"deleted": True, "city": city}
