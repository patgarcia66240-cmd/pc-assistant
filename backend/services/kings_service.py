"""Fiches complètes des rois de France (Clovis Ier -> Louis-Philippe Ier), servies depuis une
base SQLite locale (backend/data/kings.db) plutôt que par appel à l'IA générative — demande
explicite de l'utilisatrice ("toujours dans sqlite pour ne pas appeler pour rien l'ia").

Se déclenche avec le mot « roi » ou « rois » (même logique que « bourse »/« cours » pour la
finance — voir market_service.py) : « roi Louis XIV », « roi de France Louis XIV », « roi
Charlemagne », « roi saint louis », « roi louis 14 » (numéro arabe accepté, converti en chiffres
romains pour la recherche) reconnaissent tous le même roi. Risque connu et accepté (même logique
que « cours ») : « roi » est un mot français courant hors contexte historique (« être au petit
soin comme un roi », « le roi du pétrole »...) — un message qui le contient sans nom de roi
reconnu tombe sur un message clair (voir get_king_answer : requête vide ou aucun roi trouvé),
jamais sur l'IA générale qui pourrait halluciner une date ou un événement historique.

Demande explicite de l'utilisatrice : « rois » seul (pluriel) ou « roi »/« roi de france » sans
nom précis (rien à chercher après extraction) affiche la liste chronologique complète des 85 rois
(naissance, règne, et mort OU raison de fin de règne si le règne ne s'est pas terminé par une mort
en exercice — déposition/abdication/déchéance, voir REIGN_END_REASONS dans build_kings_db.py,
vérifié à la main sur les quelques rois concernés) plutôt qu'un message d'aide générique (voir
get_king_list_text).

Données : 85 rois, de Clovis Ier (Mérovingiens, ~481) à Louis-Philippe Ier (Bourbon-Orléans,
1830-1848), construits via recherche web vérifiée (5 lots par dynastie/ère, voir
build_kings_db.py à la racine du projet backend pour la provenance). Chaque roi porte, quand
l'information a été trouvée de façon fiable : dates de règne/naissance/mort (avec indicateur
"approximatif" quand la source elle-même est incertaine — fréquent pour les rois mérovingiens,
très mal documentés), épouse(s), favorites/maîtresses connues, enfants notables, guerres/
événements majeurs du règne, anecdotes (les légendes non avérées sont explicitement signalées
comme telles dans le texte, jamais présentées comme des faits). Un champ non trouvé de façon
fiable est vide plutôt qu'inventé — c'est normal, surtout pour les rois les plus anciens.

Note technique : sqlite3 (synchrone) est utilisé plutôt qu'aiosqlite car la base est locale, minus
scule (85 rois) et les requêtes sont quasi instantanées — l'ajout d'une couche async n'apporterait
rien ici et complexifierait le code pour rien.
"""
import re
import sqlite3
from pathlib import Path

from services.local_service import normalize_text, _strip_filler_suffix

# Chemin de la base construite par build_kings_db.py (voir la racine du projet backend). Chemin
# relatif au dossier backend/ (là où uvicorn est lancé), comme le reste du projet.
KINGS_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kings.db"

_ROMAN_VALUES = [
    (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"),
]


def _arabic_to_roman(n: int) -> str:
    result = ""
    for value, symbol in _ROMAN_VALUES:
        while n >= value:
            result += symbol
            n -= value
    return result


def _normalize_search(text: str) -> str:
    """Même logique de normalisation que build_kings_db.py (search_name en base) : accents
    retirés, minuscules, tout caractère non alphanumérique remplacé par une espace."""
    normalized = normalize_text(text)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return normalized.strip()


def is_king_request(message: str) -> bool:
    normalized = normalize_text(message)
    return bool(re.search(r"\brois?\b", normalized))


def extract_king_query(message: str) -> str | None:
    normalized = normalize_text(message)
    # "de\s+france\b" (pas "de\s+france\s+") : sinon "roi de france" sans rien après ne matche
    # pas cette alternative (aucune espace après "france" en fin de chaîne) et retombe sur "de\s+"
    # tout court, qui laisse "france" comme requête -> bug constaté, corrigé ici.
    match = re.search(
        r"\brois?\b\s*(?:de\s+france\b\s*|des\s+francais\b\s*|de\s+)?(.*)$", normalized
    )
    if not match:
        return None
    query = match.group(1).strip(" ?.!\t")
    query = _strip_filler_suffix(query)
    return query or None


def _query_variants(raw_query: str) -> list:
    """Génère les formes à essayer en base : la requête normalisée telle quelle, et — si elle se
    termine par un numéro écrit en chiffres arabes ("louis 14") — la même chose convertie en
    chiffres romains ("louis xiv"), qui est le format utilisé dans les noms en base."""
    variants = []
    base = _normalize_search(raw_query)
    if base:
        variants.append(base)

    match = re.match(r"^(.*?)\s+(\d{1,2})$", raw_query.strip())
    if match:
        name_part, num_str = match.groups()
        num = int(num_str)
        if 1 <= num <= 50:
            roman_query = f"{name_part} {_arabic_to_roman(num)}"
            roman_normalized = _normalize_search(roman_query)
            if roman_normalized and roman_normalized not in variants:
                variants.append(roman_normalized)
    return variants


def _connect():
    conn = sqlite3.connect(KINGS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _find_kings(conn, query_normalized: str) -> list:
    rows = conn.execute(
        "SELECT * FROM kings WHERE search_name = ? OR search_alt_name = ? ORDER BY sort_order",
        (query_normalized, query_normalized),
    ).fetchall()
    if rows:
        return rows
    like_pattern = f"{query_normalized}%"
    return conn.execute(
        "SELECT * FROM kings WHERE search_name LIKE ? OR search_alt_name LIKE ? ORDER BY sort_order",
        (like_pattern, like_pattern),
    ).fetchall()


def _format_date(raw, approx) -> str | None:
    if not raw:
        return None
    if approx and not re.search(r"\b(vers|circa|avant|apr[eè]s|entre|ou)\b", raw, re.IGNORECASE):
        return f"vers {raw}"
    return raw


def _display_name(row) -> str:
    return f"{row['name']} ({row['alt_name']})" if row["alt_name"] else row["name"]


def _format_king_text(row, spouses, favorites, children, wars, anecdotes) -> str:
    name = _display_name(row)
    dynasty = f" — {row['dynasty']}" if row["dynasty"] else ""
    reign_start = _format_date(row["reign_start"], row["reign_start_approx"])
    reign_end = _format_date(row["reign_end"], row["reign_end_approx"])
    reign = f"règne de {reign_start} à {reign_end}" if (reign_start and reign_end) else (
        f"règne à partir de {reign_start}" if reign_start else "dates de règne non trouvées de façon fiable"
    )
    birth = _format_date(row["birth_date"], row["birth_date_approx"])
    death = _format_date(row["death_date"], row["death_date_approx"])
    birth_death = ""
    if birth or death:
        parts = []
        if birth:
            parts.append(f"né(e) {birth}")
        if death:
            parts.append(f"mort(e) {death}")
        birth_death = " (" + ", ".join(parts) + ")"

    lines = [f"{name}{dynasty} — {reign}{birth_death}."]

    if spouses:
        items = "; ".join(s["name"] + (f" ({s['notes']})" if s["notes"] else "") for s in spouses)
        lines.append(f"Épouse(s) : {items}.")
    if favorites:
        items = "; ".join(f["name"] + (f" ({f['notes']})" if f["notes"] else "") for f in favorites)
        lines.append(f"Favorites : {items}.")
    if children:
        items = "; ".join(c["name"] + (f" ({c['notes']})" if c["notes"] else "") for c in children)
        lines.append(f"Enfants notables : {items}.")
    if wars:
        items = "; ".join(
            w["name"] + (f" ({w['years']})" if w["years"] else "") + (f" — {w['notes']}" if w["notes"] else "")
            for w in wars
        )
        lines.append(f"Guerres/événements : {items}.")
    if anecdotes:
        items = " ".join(a["text"] for a in anecdotes)
        lines.append(f"Anecdotes : {items}")

    return "\n".join(lines)


def _format_reign_range(row) -> str:
    """"1643-05-14 à 1715-09-01" plutôt qu'un tiret ambigu entre deux dates ISO (ex.
    "814-840-06-20" est illisible : on ne sait plus où finit une date et où commence l'autre —
    bug constaté en pratique dans le message de désambiguïsation, corrigé en centralisant le
    format ici pour qu'il serve aussi bien la liste complète que la désambiguïsation)."""
    reign_start = _format_date(row["reign_start"], row["reign_start_approx"]) or "?"
    reign_end = _format_date(row["reign_end"], row["reign_end_approx"]) or "?"
    return f"{reign_start} à {reign_end}"


def _format_list_line(row) -> str:
    name = _display_name(row)
    dynasty = f" ({row['dynasty']})" if row["dynasty"] else ""
    birth = _format_date(row["birth_date"], row["birth_date_approx"])
    reign_range = _format_reign_range(row)
    death = _format_date(row["death_date"], row["death_date_approx"])
    reason = row["reign_end_reason"]  # rempli seulement pour déposition/abdication/déchéance

    birth_part = f"né {birth}" if birth else "naissance inconnue"
    reign_part = f"règne {reign_range}"
    if reason:
        reign_part += f" ({reason})"
    death_part = f", mort {death}" if death else ""

    return f"{name}{dynasty} — {birth_part}, {reign_part}{death_part}."


def _king_summary(row) -> dict:
    """Version compacte d'un roi pour la frise chronologique (frontend) : juste ce qu'il faut
    pour afficher une ligne lisible (nom, dynastie, dates, raison de fin de règne si non-mort en
    exercice) — pas les épouses/enfants/guerres/anecdotes, réservés à la fiche d'un roi précis
    (voir get_king_answer, clé "king"). Toujours depuis SQLite, jamais inventé."""
    return {
        "name": _display_name(row),
        "dynasty": row["dynasty"],
        "reign_start": row["reign_start"],
        "reign_end": row["reign_end"],
        "birth_date": row["birth_date"],
        "death_date": row["death_date"],
        "reign_end_reason": row["reign_end_reason"],
    }


def get_all_kings_summary(conn) -> list:
    rows = conn.execute("SELECT * FROM kings ORDER BY sort_order").fetchall()
    return [_king_summary(row) for row in rows]


def get_king_list_text(conn) -> str:
    """Liste chronologique complète : naissance, règne, et mort — ou raison de fin de règne
    (déposition/abdication/déchéance) quand le règne ne s'est pas terminé par une mort en
    exercice, voir REIGN_END_REASONS dans build_kings_db.py. Demande explicite de l'utilisatrice
    pour « rois » seul ou « roi »/« roi de france » sans nom précis."""
    rows = conn.execute("SELECT * FROM kings ORDER BY sort_order").fetchall()
    lines = [_format_list_line(row) for row in rows]
    header = f"Liste complète des {len(rows)} rois de France (Clovis Ier à Louis-Philippe Ier) :"
    return header + "\n" + "\n".join(lines)


async def get_king_answer(message: str) -> dict:
    raw_query = extract_king_query(message)

    if not KINGS_DB_PATH.exists():
        return {
            "text": "La base des rois de France n'est pas installée (fichier data/kings.db manquant).",
            "king": None,
            "kings_list": None,
        }

    conn = _connect()
    try:
        if not raw_query:
            # « rois » seul, ou « roi »/« roi de france » sans nom précis -> liste complète
            # (demande explicite), pas un simple message d'aide. kings_list : version compacte
            # des 85 rois pour que le frontend affiche une frise chronologique plutôt que du texte
            # brut (demande explicite : "faire une frise pour rois de france").
            return {"text": get_king_list_text(conn), "king": None, "kings_list": get_all_kings_summary(conn)}

        rows = []
        for variant in _query_variants(raw_query):
            rows = _find_kings(conn, variant)
            if rows:
                break

        if not rows:
            return {
                "text": (
                    f"Je ne trouve pas de roi correspondant à « {raw_query} ». La base couvre les "
                    "rois de France de Clovis Ier à Louis-Philippe Ier (1848), ex. « roi François "
                    "Ier », « roi Henri IV », « roi Louis XVI »."
                ),
                "king": None,
                "kings_list": None,
            }

        if len(rows) > 1:
            options = "; ".join(
                f"{_display_name(r)} (règne {_format_reign_range(r)})" for r in rows
            )
            # Même logique que la liste complète : la frise vaut mieux qu'un mur de texte pour
            # comparer plusieurs rois homonymes (ex. "rois louis" -> les 18 Louis).
            return {
                "text": (
                    f"Plusieurs rois correspondent à « {raw_query} » : {options}. Précise le "
                    "numéro, ex. « roi clovis 2 »."
                ),
                "king": None,
                "kings_list": [_king_summary(r) for r in rows],
            }

        row = rows[0]
        king_id = row["id"]
        spouses = conn.execute("SELECT * FROM spouses WHERE king_id = ?", (king_id,)).fetchall()
        favorites = conn.execute("SELECT * FROM favorites WHERE king_id = ?", (king_id,)).fetchall()
        children = conn.execute("SELECT * FROM children WHERE king_id = ?", (king_id,)).fetchall()
        wars = conn.execute("SELECT * FROM wars_events WHERE king_id = ?", (king_id,)).fetchall()
        anecdotes = conn.execute("SELECT * FROM anecdotes WHERE king_id = ?", (king_id,)).fetchall()

        text = _format_king_text(row, spouses, favorites, children, wars, anecdotes)

        return {
            "text": text,
            "king": {
                "name": _display_name(row),
                "dynasty": row["dynasty"],
                "reign_start": row["reign_start"],
                "reign_end": row["reign_end"],
                "birth_date": row["birth_date"],
                "death_date": row["death_date"],
                "spouses": [dict(s) for s in spouses],
                "favorites": [dict(f) for f in favorites],
                "children": [dict(c) for c in children],
                "wars_events": [dict(w) for w in wars],
                "anecdotes": [a["text"] for a in anecdotes],
            },
            "kings_list": None,
        }
    finally:
        conn.close()
