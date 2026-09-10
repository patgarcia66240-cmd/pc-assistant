"""Construit backend/data/prenoms_extra.json : infos "origine/popularité du prénom" pour la
carte Saint du jour (étymologie + statistiques de naissances réelles).

Pourquoi un script à part plutôt que des données livrées directement : le sandbox de dev n'a
pas accès à data.gouv.fr/insee.fr (politique réseau), donc ces données doivent être téléchargées
depuis TA machine, avec ta propre connexion. Aucune valeur n'est inventée ici : si une source ne
répond pas ou qu'une colonne attendue est absente, le script le signale et passe à la suite plutôt
que de deviner.

Sources (vérifiées le 10/09/2026) :
- Popularité : fichier officiel INSEE "Prénoms depuis 1900" (data.gouv.fr, Licence Ouverte 2.0,
  https://www.data.gouv.fr/datasets/fichier-des-prenoms-depuis-1900) — naissances par prénom/sexe/
  année, France entière, depuis 1900.
- Origine/signification : dataset tiers "Prénoms français INSEE 1900-2024 enrichi (Super Prénom)"
  (data.gouv.fr, CC BY 4.0, https://www.data.gouv.fr/datasets/prenoms-francais-insee-1900-2024-
  enrichi-super-prenom) — curation indépendante croisant le fichier INSEE avec des données
  d'étymologie. Moins "officiel" que l'INSEE pour ce volet : les entrées gardent une formulation
  prudente côté frontend plutôt qu'une affirmation catégorique.

Usage : cd backend && python build_prenoms_extra.py
Sortie : backend/data/prenoms_extra.json (clé = prénom de base tel qu'utilisé dans
saints_calendar.json, ex. "Inès", "Jean-Baptiste").
"""
import csv
import io
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import httpx


def strip_accents(text: str) -> str:
    """Le fichier INSEE stocke les prénoms en majuscules sans accents (ex. "INES", "JEROME") :
    la comparaison doit ignorer les accents pour retrouver "Inès", "Jérôme", etc."""
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn").lower()

HERE = Path(__file__).resolve().parent
SAINTS_CALENDAR_PATH = HERE / "data" / "saints_calendar.json"
OUTPUT_PATH = HERE / "data" / "prenoms_extra.json"

INSEE_DATASET_API = "https://www.data.gouv.fr/api/1/datasets/fichier-des-prenoms-depuis-1900/"
SUPER_PRENOM_DATASET_API = "https://www.data.gouv.fr/api/1/datasets/prenoms-francais-insee-1900-2024-enrichi-super-prenom/"


def normalize_first_name(raw_name: str) -> str:
    cleaned = raw_name
    for prefix in ("Sainte ", "Saints ", "Saint "):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    return cleaned.split(",")[0].split(" et ")[0].strip()


def load_target_names() -> set[str]:
    with SAINTS_CALENDAR_PATH.open(encoding="utf-8") as f:
        calendar = json.load(f)
    names = {normalize_first_name(entry["name"]) for entry in calendar.values()}
    print(f"[1/4] {len(names)} prénoms de base à chercher (depuis saints_calendar.json).")
    return names


def find_resource_url(client: httpx.Client, dataset_api_url: str, title_keywords: list[str]) -> str | None:
    """Interroge l'API dataset de data.gouv.fr et retourne l'URL du premier resource CSV dont le
    titre contient l'un des mots-clés (insensible à la casse). Évite de coder en dur un ID de
    resource qui pourrait changer."""
    response = client.get(dataset_api_url, timeout=15)
    response.raise_for_status()
    resources = response.json().get("resources", [])
    for resource in resources:
        title = (resource.get("title") or "").lower()
        fmt = (resource.get("format") or "").lower()
        if fmt != "csv":
            continue
        if any(kw in title for kw in title_keywords):
            return resource.get("url")
    return None


def detect_column(fieldnames: list[str], candidates: list[str]) -> str | None:
    lowered = {fn.lower(): fn for fn in fieldnames}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    return None


def build_popularity(client: httpx.Client, target_names: set[str]) -> dict:
    print("[2/4] Recherche du fichier INSEE officiel des prénoms sur data.gouv.fr...")
    url = find_resource_url(client, INSEE_DATASET_API, title_keywords=["nat", "national", "prenom"])
    if not url:
        print("  -> Aucune resource CSV trouvée pour ce dataset, popularité ignorée.")
        return {}
    print(f"  -> {url}")
    resp = client.get(url, timeout=60)
    resp.raise_for_status()
    text = resp.content.decode("utf-8", errors="replace")
    delimiter = ";" if text.count(";") > text.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    fieldnames = reader.fieldnames or []
    name_col = detect_column(fieldnames, ["preusuel", "prenom", "prénom"])
    year_col = detect_column(fieldnames, ["annais", "periode", "annee", "année"])
    count_col = detect_column(fieldnames, ["nombre", "valeur"])
    if not (name_col and year_col and count_col):
        print(f"  -> Colonnes attendues introuvables dans {fieldnames}, popularité ignorée.")
        return {}

    totals = defaultdict(int)
    peak = {}  # name -> (year, count)
    target_lookup = {strip_accents(n): n for n in target_names}
    rows_read = 0
    for row in reader:
        rows_read += 1
        raw_name = (row.get(name_col) or "").strip()
        if not raw_name:
            continue
        key = raw_name.title()
        norm_key = strip_accents(key)
        if norm_key not in target_lookup:
            continue
        try:
            count = int(row.get(count_col) or 0)
            year = int(row.get(year_col) or 0)
        except ValueError:
            continue
        totals[key] += count
        if key not in peak or count > peak[key][1]:
            peak[key] = (year, count)

    print(f"  -> {rows_read} lignes lues, {len(totals)} prénoms cibles trouvés.")
    result = {}
    for key, total in totals.items():
        original_name = target_lookup[strip_accents(key)]
        year, count = peak.get(key, (None, None))
        result[original_name] = {
            "total_births_since_1900": total,
            "peak_year": year,
            "peak_year_births": count,
        }
    return result


def build_etymology(client: httpx.Client, target_names: set[str]) -> dict:
    print("[3/4] Recherche du dataset Super Prénom (origine/signification) sur data.gouv.fr...")
    url = find_resource_url(client, SUPER_PRENOM_DATASET_API, title_keywords=["origine", "fete", "fête"])
    if not url:
        print("  -> Aucune resource CSV trouvée pour ce dataset, origine/signification ignorées.")
        return {}
    print(f"  -> {url}")
    resp = client.get(url, timeout=60)
    resp.raise_for_status()
    text = resp.content.decode("utf-8", errors="replace")
    delimiter = ";" if text.count(";") > text.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    fieldnames = reader.fieldnames or []
    name_col = detect_column(fieldnames, ["prenom", "prénom"])
    origine_col = detect_column(fieldnames, ["origine"])
    signif_col = detect_column(fieldnames, ["signification", "etymologie", "étymologie"])
    if not name_col or not (origine_col or signif_col):
        print(f"  -> Colonnes attendues introuvables dans {fieldnames}, origine/signification ignorées.")
        return {}

    target_lookup = {strip_accents(n): n for n in target_names}
    result = {}
    matched = 0
    for row in reader:
        raw_name = (row.get(name_col) or "").strip()
        if not raw_name or strip_accents(raw_name) not in target_lookup:
            continue
        origine = (row.get(origine_col) or "").strip() if origine_col else ""
        signification = (row.get(signif_col) or "").strip() if signif_col else ""
        if not origine and not signification:
            continue
        matched += 1
        result[target_lookup[strip_accents(raw_name)]] = {
            "origine": origine or None,
            "signification": signification or None,
        }
    print(f"  -> {matched} prénoms cibles avec origine/signification trouvés.")
    return result


def main() -> int:
    target_names = load_target_names()
    with httpx.Client(headers={"User-Agent": "pc-assistant-build-script/1.0"}) as client:
        try:
            popularity = build_popularity(client, target_names)
        except httpx.HTTPError as error:
            print(f"  -> Échec réseau sur la popularité INSEE ({error}), section ignorée.")
            popularity = {}
        try:
            etymology = build_etymology(client, target_names)
        except httpx.HTTPError as error:
            print(f"  -> Échec réseau sur l'origine/signification ({error}), section ignorée.")
            etymology = {}

    print("[4/4] Fusion et écriture de prenoms_extra.json...")
    merged = {}
    for name in set(popularity) | set(etymology):
        merged[name] = {**popularity.get(name, {}), **etymology.get(name, {})}

    if not merged:
        print("Aucune donnée récupérée (pas de réseau, ou sources indisponibles) : "
              "prenoms_extra.json n'est PAS écrit, la section restera simplement absente de l'app.")
        return 1

    OUTPUT_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"OK : {len(merged)} prénoms écrits dans {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
