"""Construit backend/data/kings.db à partir des 5 fichiers JSON de recherche (un par dynastie/ère).

Usage : python3 build_kings_db.py <dossier_json> <sortie.db>

Schéma : une table `kings` (un roi par ligne, avec sort_order pour l'ordre chronologique) et des
tables enfants `spouses`/`favorites`/`children`/`wars_events`/`anecdotes`/`sources` (clé étrangère
king_id). `kings.search_name` est une version normalisée du nom (accents retirés, minuscules) pour
la recherche ; `kings.alt_name` extrait un surnom entre parenthèses du nom d'origine (ex. "Louis IX
(Saint Louis)" -> name="Louis IX", alt_name="Saint Louis") pour permettre "roi saint louis" en plus
de "roi louis 9".

`kings.reign_end_reason` : NULL pour l'immense majorité (le roi est mort en exercice — reign_end
et death_date coïncident). Rempli seulement pour les rois dont le règne s'est terminé autrement
(déposition, abdication...), via REIGN_END_REASONS ci-dessous — vérifié à la main à partir des
anecdotes/événements déjà présents dans les JSON de recherche pour CES rois précis (pas une
supposition globale), utile pour "rois" / "roi de france" seuls (liste complète avec naissance,
règne, et mort OU raison de fin de règne — demande explicite de l'utilisatrice).
"""
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

SCHEMA = """
CREATE TABLE kings (
    id INTEGER PRIMARY KEY,
    sort_order INTEGER NOT NULL,
    name TEXT NOT NULL,
    alt_name TEXT,
    search_name TEXT NOT NULL,
    search_alt_name TEXT,
    dynasty TEXT,
    reign_start TEXT,
    reign_start_approx INTEGER DEFAULT 0,
    reign_end TEXT,
    reign_end_approx INTEGER DEFAULT 0,
    birth_date TEXT,
    birth_date_approx INTEGER DEFAULT 0,
    death_date TEXT,
    death_date_approx INTEGER DEFAULT 0,
    reign_end_reason TEXT
);
CREATE INDEX idx_kings_search_name ON kings(search_name);
CREATE INDEX idx_kings_search_alt_name ON kings(search_alt_name);
CREATE INDEX idx_kings_sort_order ON kings(sort_order);

CREATE TABLE spouses (
    id INTEGER PRIMARY KEY,
    king_id INTEGER NOT NULL REFERENCES kings(id),
    name TEXT NOT NULL,
    notes TEXT
);
CREATE INDEX idx_spouses_king_id ON spouses(king_id);

CREATE TABLE favorites (
    id INTEGER PRIMARY KEY,
    king_id INTEGER NOT NULL REFERENCES kings(id),
    name TEXT NOT NULL,
    notes TEXT
);
CREATE INDEX idx_favorites_king_id ON favorites(king_id);

CREATE TABLE children (
    id INTEGER PRIMARY KEY,
    king_id INTEGER NOT NULL REFERENCES kings(id),
    name TEXT NOT NULL,
    notes TEXT
);
CREATE INDEX idx_children_king_id ON children(king_id);

CREATE TABLE wars_events (
    id INTEGER PRIMARY KEY,
    king_id INTEGER NOT NULL REFERENCES kings(id),
    name TEXT NOT NULL,
    years TEXT,
    notes TEXT
);
CREATE INDEX idx_wars_events_king_id ON wars_events(king_id);

CREATE TABLE anecdotes (
    id INTEGER PRIMARY KEY,
    king_id INTEGER NOT NULL REFERENCES kings(id),
    text TEXT NOT NULL
);
CREATE INDEX idx_anecdotes_king_id ON anecdotes(king_id);

CREATE TABLE sources (
    id INTEGER PRIMARY KEY,
    king_id INTEGER NOT NULL REFERENCES kings(id),
    url TEXT NOT NULL
);
CREATE INDEX idx_sources_king_id ON sources(king_id);
"""

# Rois dont le règne ne s'est PAS terminé par une mort en exercice (déposition, abdication...) :
# vérifié à la main d'après les anecdotes/wars_events déjà collectés pour ces rois précis (voir
# kings_merovingiens.json/kings_bourbons.json), pas une supposition. Clé = `name` tel qu'écrit
# dans le JSON source (avant extraction de l'alt_name éventuel).
REIGN_END_REASONS = {
    "Childéric III": "déposé",  # déposé par Pépin le Bref en 751, tonsuré et envoyé au monastère
    "Charles III le Gros": "déposé",  # déposé à Tribur en novembre 887
    "Charles III le Simple": "déposé (emprisonné)",  # déposé en 923, mort en captivité en 929
    "Louis XVI": "déchu",  # chute de la monarchie le 10 août 1792, guillotiné en 1793
    "Charles X": "abdication",  # Révolution de Juillet 1830
    "Louis-Philippe Ier": "abdication",  # Révolution de février 1848
}

# Ordre chronologique des lots (déjà chronologique DANS chaque fichier, voir historique des
# recherches menées pour ce projet).
FILES_IN_ORDER = [
    "kings_merovingiens.json",
    "kings_carolingiens.json",
    "kings_capetiens.json",
    "kings_valois.json",
    "kings_bourbons.json",
]

ALT_NAME_RE = re.compile(r"^(.*?)\s*\(([^)]+)\)\s*$")


def normalize_search(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()


def split_name(raw_name: str):
    """"Louis IX (Saint Louis)" -> ("Louis IX", "Saint Louis"). Sans parenthèses -> (raw_name, None)."""
    match = ALT_NAME_RE.match(raw_name)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return raw_name.strip(), None


def to_int(value) -> int:
    if isinstance(value, bool):
        return int(value)
    return 1 if value else 0


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 build_kings_db.py <dossier_json> <sortie.db>")
        sys.exit(1)
    json_dir = Path(sys.argv[1])
    db_path = Path(sys.argv[2])

    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)

    sort_order = 0
    total_kings = 0
    warnings = []

    for filename in FILES_IN_ORDER:
        path = json_dir / filename
        kings = json.loads(path.read_text(encoding="utf-8"))
        for king in kings:
            sort_order += 1
            raw_name = king.get("name") or ""
            name, alt_name = split_name(raw_name)

            cur = conn.execute(
                """INSERT INTO kings
                   (sort_order, name, alt_name, search_name, search_alt_name, dynasty,
                    reign_start, reign_start_approx, reign_end, reign_end_approx,
                    birth_date, birth_date_approx, death_date, death_date_approx,
                    reign_end_reason)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    sort_order,
                    name,
                    alt_name,
                    normalize_search(name),
                    normalize_search(alt_name) if alt_name else None,
                    king.get("dynasty"),
                    king.get("reign_start"),
                    to_int(king.get("reign_start_approx")),
                    king.get("reign_end"),
                    to_int(king.get("reign_end_approx")),
                    king.get("birth_date"),
                    to_int(king.get("birth_date_approx")),
                    king.get("death_date"),
                    to_int(king.get("death_date_approx")),
                    REIGN_END_REASONS.get(raw_name),
                ),
            )
            king_id = cur.lastrowid
            total_kings += 1

            for spouse in king.get("spouses") or []:
                if not spouse.get("name"):
                    continue
                conn.execute(
                    "INSERT INTO spouses (king_id, name, notes) VALUES (?, ?, ?)",
                    (king_id, spouse.get("name"), spouse.get("notes")),
                )
            for favorite in king.get("favorites") or []:
                if not favorite.get("name"):
                    continue
                conn.execute(
                    "INSERT INTO favorites (king_id, name, notes) VALUES (?, ?, ?)",
                    (king_id, favorite.get("name"), favorite.get("notes")),
                )
            for child in king.get("children") or []:
                if not child.get("name"):
                    continue
                conn.execute(
                    "INSERT INTO children (king_id, name, notes) VALUES (?, ?, ?)",
                    (king_id, child.get("name"), child.get("notes")),
                )
            for event in king.get("wars_events") or []:
                if not event.get("name"):
                    continue
                conn.execute(
                    "INSERT INTO wars_events (king_id, name, years, notes) VALUES (?, ?, ?, ?)",
                    (king_id, event.get("name"), event.get("years"), event.get("notes")),
                )
            for anecdote in king.get("anecdotes") or []:
                if not anecdote:
                    continue
                conn.execute(
                    "INSERT INTO anecdotes (king_id, text) VALUES (?, ?)",
                    (king_id, anecdote),
                )
            for source_url in king.get("sources") or []:
                if not source_url:
                    continue
                conn.execute(
                    "INSERT INTO sources (king_id, url) VALUES (?, ?)",
                    (king_id, source_url),
                )

        print(f"{filename}: {len(kings)} rois")

    # Vérifie les doublons de search_name (homonymes exacts type "Clovis III" listé deux fois
    # sous des numérotations concurrentes) -> juste un avertissement, pas bloquant : le service
    # gèrera la désambiguïsation par dates de règne le cas échéant.
    dupes = conn.execute(
        "SELECT search_name, COUNT(*) c FROM kings GROUP BY search_name HAVING c > 1"
    ).fetchall()
    if dupes:
        warnings.append(f"Noms en double (search_name) : {dupes}")

    conn.commit()
    conn.close()

    print(f"\nTotal : {total_kings} rois insérés dans {db_path}")
    if warnings:
        print("\nAvertissements :")
        for w in warnings:
            print(" -", w)


if __name__ == "__main__":
    main()
