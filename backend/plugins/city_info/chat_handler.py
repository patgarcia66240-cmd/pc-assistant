"""Handler de chat pour les infos ville/département/région — extrait de routes/chat.py le
12/09/2026 (voir ram/heure_meteo/bourse/calendar pour le reste du même chantier). Regroupe 4 cas
qui étaient 4 blocs `if` séparés dans chat.py : l'ORDRE compte, exactement comme avant
(actualisation > département > région > ville, chacun avec son propre préfixe à retirer du
message avant de l'envoyer au service) — matches() les couvre tous, handle() les redépartage dans
le même ordre.

Erreurs : LookupError (ville/département/région introuvable) est traitée à part, en 404 avec le
message exact du service, PAS via le mécanisme générique de plugin_loader (qui transformerait
n'importe quelle SERVICE_ERRORS, LookupError inclus, en 502 générique avec chat_error_message) —
c'était le comportement d'origine dans chat.py, préservé ici volontairement. httpx.HTTPError/
IndexError/KeyError remontent tels quels : le mécanisme générique les convertit en 502 avec
chat_error_message ("City information service unavailable"), comme avant."""
import re

from fastapi import HTTPException

from services.city_info_service import (
    fetch_departement_info,
    fetch_region_info,
    get_city_info,
    is_city_info_request,
    is_city_refresh_request,
    is_departement_info_request,
    is_region_info_request,
)


def matches(message: str) -> bool:
    return (
        is_city_refresh_request(message)
        or is_departement_info_request(message)
        or is_region_info_request(message)
        or is_city_info_request(message)
    )


async def handle(message: str, context: dict) -> dict:
    if is_city_refresh_request(message):
        query = re.sub(
            r"^(?:maj|force|actualiser?|rafra[iî]chis|mets?\s+à\s+jour)\s+infos?(?:\s+sur)?\s+",
            "",
            message.strip(),
            flags=re.IGNORECASE,
        )
        try:
            city_info = await get_city_info(query, force_refresh=True)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return {
            "response": f"Informations actualisées sur {city_info['city']}",
            "data": city_info,
            "source": "local",
            "source_type": "city_info",
        }

    if is_departement_info_request(message):
        query = re.sub(r"^(?:infos?|informations?)\s+d[ée]partements?\s+", "", message.strip(), flags=re.IGNORECASE)
        try:
            dept_info = await fetch_departement_info(query)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return {
            "response": f"Informations sur le département {dept_info['nom']}",
            "data": dept_info,
            "source": "local",
            "source_type": "departement_info",
        }

    if is_region_info_request(message):
        query = re.sub(r"^(?:infos?|informations?)\s+r[ée]gions?\s+", "", message.strip(), flags=re.IGNORECASE)
        try:
            region_info = await fetch_region_info(query)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return {
            "response": f"Informations sur la région {region_info['nom']}",
            "data": region_info,
            "source": "local",
            "source_type": "region_info",
        }

    # is_city_info_request(message) — dernier cas possible, garanti par matches() ci-dessus.
    query = re.sub(r"^(?:infos?|informations?)(?:\s+sur)?\s+", "", message.strip(), flags=re.IGNORECASE)
    try:
        city_info = await get_city_info(query)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {
        "response": f"Informations sur {city_info['city']}",
        "data": city_info,
        "source": "local",
        "source_type": "city_info",
    }
