"""
Fase 1: subida de datos en bruto (ver README).

Lee los CSV de una carpeta (nameMachine_MYearMonth.csv, separados por
tabulador, 2 filas de cabecera) y los inserta tal cual en measurements_raw.
No se valida ni formatea nada aqui: eso es la fase 2 (checker) y 3 (formatter).
"""

import argparse
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "ferlo.db"
SCHEMA_PATH = ROOT / "database" / "schema.sql"
CSV_ENCODING = "cp1252"



DELIMITER_LIST = {
    "\t": "tabulador",
    ";": "punto y coma",
    ",": "coma",
    "|": "barra vertical",
}

MACHINES = ["F1", "F2", "F3", "F4", "F5"]


def machine_folder(machine: str) -> Path:
    return ROOT / "data" / f"{machine}_csv"


def ensure_schema(conn: sqlite3.Connection) -> None:
    has_tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='files'"
    ).fetchone()
    if not has_tables:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        return

    columns = {row[1] for row in conn.execute("PRAGMA table_info(measurements_raw)")}
    if "machine" not in columns:
        conn.execute("ALTER TABLE measurements_raw ADD COLUMN machine TEXT")
        conn.execute(
            """UPDATE measurements_raw
               SET machine = (SELECT machine FROM files WHERE files.id = measurements_raw.file_id)
               WHERE machine IS NULL"""
        )
        conn.commit()


def already_imported(conn: sqlite3.Connection, filename: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM files WHERE filename = ?", (filename,)
    ).fetchone() is not None


def detect_delimiter(csv_path: Path) -> str:
    first_line = csv_path.open(encoding=CSV_ENCODING).readline()
    for delimiter in DELIMITER_LIST:
        if delimiter in first_line:
            return delimiter
    return next(iter(DELIMITER_LIST))  # tabulador por defecto


def import_file(conn: sqlite3.Connection, csv_path: Path, machine: str) -> int:
    delimiter = detect_delimiter(csv_path)

    cur = conn.execute(
        "INSERT INTO files (filename, machine) VALUES (?, ?)",
        (csv_path.name, machine),
    )
    file_id = cur.lastrowid

    with csv_path.open(newline="", encoding=CSV_ENCODING) as f:
        reader = csv.reader(f, delimiter=delimiter)
        next(reader)  # cabecera 1: nombres de columna
        next(reader)  # cabecera 2: formato de columna
        rows = [
            (file_id, machine, row[0], row[1], row[2], row[3])
            for row in reader
            if len(row) >= 4
        ]

    conn.executemany(
        """INSERT INTO measurements_raw
           (file_id, machine, date_raw, time_raw, temperature_raw, pressure_raw)
           VALUES (?, ?, ?, ?, ?, ?)""",
        rows,
    )
    return len(rows)


def import_folder(conn: sqlite3.Connection, folder: Path, machine: str) -> tuple[int, int, int]:
    csv_files = sorted(folder.glob("*.csv"))
    if not csv_files:
        print(f"No se encontraron CSV en {folder}")
        return 0, 0, 0

    skipped = 0
    rows = 0
    for csv_path in csv_files:
        if already_imported(conn, csv_path.name):
            print(f"{csv_path.name}: ya importado, se omite")
            skipped += 1
            continue
        n = import_file(conn, csv_path, machine)
        rows += n
        print(f"{csv_path.name}: {n} filas")
    return len(csv_files), skipped, rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importa los CSV de esterilizacion a measurements_raw. "
        "Sin argumentos, importa la lista completa de maquinas (F1 a F5)."
    )
    parser.add_argument(
        "-m", "--machine",
        choices=MACHINES,
        help="Importar solo la maquina indicada (F1-F5) en vez de la lista completa.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    machines = [args.machine] if args.machine else MACHINES

    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_schema(conn)
        files_total = 0
        skipped_total = 0
        rows_total = 0
        for machine in machines:
            files, skipped, rows = import_folder(conn, machine_folder(machine), machine)
            files_total += files
            skipped_total += skipped
            rows_total += rows
        conn.commit()
        print(
            f"\nTotal: {files_total - skipped_total} archivos importados, "
            f"{skipped_total} omitidos, {rows_total} filas insertadas"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
