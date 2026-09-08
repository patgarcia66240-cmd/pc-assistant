"""Populate the SQLite city cache with European capitals."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import init_db
from services.city_info_service import cache_european_capitals


async def main():
    await init_db()
    results = await cache_european_capitals()
    cached = sum(1 for result in results if "error" not in result)
    print(f"Capitales traitees : {len(results)}")
    print(f"Fiches enregistrees : {cached}")
    print(f"Echecs : {len(results) - cached}")


if __name__ == "__main__":
    asyncio.run(main())