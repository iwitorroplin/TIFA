"""
Fase 3: formateo de datos (ver README).

Unir date_raw + time_raw en un timestamp 'YYYY-MM-DD HH:MM:SS' 
convierte temperature_raw/pressure_raw a numero (REAL) dentro
 Un valor crudo no interpretable se guarda como NULL.
"""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "ferlo.db"
SCHEMA_PATH = ROOT / "database" / "schema.sql"

# valor numerico valido: solo digitos, coma, punto o guion, con al menos un digito
NUMERIC_CASE = """
    CASE
        WHEN {col} IS NULL OR {col} = '' THEN NULL
        WHEN {col} NOT GLOB '*[^0-9,.-]*' AND {col} GLOB '*[0-9]*'
            THEN CAST(REPLACE({col}, ',', '.') AS REAL)
        ELSE NULL
    END
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(measurements)")}
    if columns and ("temperature" not in columns or "machine" not in columns):
        # measurements es derivada por completo de measurements_raw, se puede recrear sin perder nada
        conn.execute("DROP TABLE measurements")
        columns = set()
    if not columns:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def format_measurements(conn: sqlite3.Connection) -> int:
    conn.execute("DELETE FROM measurements")
    conn.execute(
        f"""
        INSERT INTO measurements (raw_id, file_id, machine, timestamp, temperature, pressure)
        SELECT
            id,
            file_id,
            machine,
            substr(date_raw, 7, 4) || '-' || substr(date_raw, 4, 2) || '-' || substr(date_raw, 1, 2)
            || ' ' ||
            CASE WHEN length(time_raw) = 7 THEN '0' || time_raw ELSE time_raw END,
            {NUMERIC_CASE.format(col='temperature_raw')},
            {NUMERIC_CASE.format(col='pressure_raw')}
        FROM measurements_raw
        """
    )
    return conn.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_schema(conn)
        n = format_measurements(conn)
        conn.commit()
        print(f"measurements: {n} filas formateadas")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
