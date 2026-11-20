#!/usr/bin/env python3
"""Initialise la base SQLite : schéma + données d'exemple (optionnel)."""

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "db" / "schema.sql"
SEED = ROOT / "db" / "seed.sql"


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialise la base de données")
    parser.add_argument(
        "-f", "--fichier",
        default=str(ROOT / "data" / "inventaire.db"),
        help="chemin du fichier SQLite (défaut: data/inventaire.db)",
    )
    parser.add_argument("--seed", action="store_true", help="insérer les données d'exemple")
    args = parser.parse_args()

    chemin = Path(args.fichier)
    chemin.parent.mkdir(parents=True, exist_ok=True)

    if chemin.exists():
        reponse = input(f"{chemin} existe déjà. Le remplacer ? [o/N] ").strip().lower()
        if reponse != "o":
            print("Annulé.")
            return 1
        chemin.unlink()

    conn = sqlite3.connect(chemin)
    try:
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        if args.seed:
            conn.executescript(SEED.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()

    print(f"Base créée : {chemin}" + (" (avec données d'exemple)" if args.seed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
