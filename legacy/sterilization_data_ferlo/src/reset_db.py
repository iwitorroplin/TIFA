"""
Borra ferlo.db y lo vuelve a crear aplicando schema.sql desde cero.
Util para empezar de nuevo tras una importacion duplicada o de prueba.
"""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "ferlo.db"
SCHEMA_PATH = ROOT / "database" / "schema.sql"


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Borrado {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
        print(f"{DB_PATH} recreado con schema.sql")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
