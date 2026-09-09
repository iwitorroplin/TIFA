"""
Fase 2: verificacion de los datos importados (ver README).

Consultas simples sobre lo ya subido a measurements_raw: filas por
archivo y cantidad de valores de TEMP. Solo lectura, no modifica nada.
"""

import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "ferlo.db"

DECIMAL_RE = re.compile(r"^\d+,\d+$")
ENTERO_RE = re.compile(r"^\d+$")



# filas por archivo
def rows_per_file(conn: sqlite3.Connection, machine: str | None = None) -> None:
    query = """
        SELECT f.machine, f.filename, COUNT(m.id) AS filas
        FROM files f
        LEFT JOIN measurements_raw m ON m.file_id = f.id
        {where}
        GROUP BY f.id
        ORDER BY f.machine, f.filename
    """
    where = "WHERE f.machine = ?" if machine else ""
    params = (machine,) if machine else ()

    print("Filas por archivo:")
    for row in conn.execute(query.format(where=where), params):
        print(f"  {row[0]}  {row[1]}: {row[2]} filas")

# valores de TEMP por maquina
def temp_summary(conn: sqlite3.Connection, machine: str | None = None) -> None:
    query = """
        SELECT f.machine,
               COUNT(m.id) AS total,
               SUM(CASE WHEN m.temperature_raw IS NULL OR m.temperature_raw = ''
                        THEN 1 ELSE 0 END) AS vacios
        FROM files f
        LEFT JOIN measurements_raw m ON m.file_id = f.id
        {where}
        GROUP BY f.machine
        ORDER BY f.machine
    """
    where = "WHERE f.machine = ?" if machine else ""
    params = (machine,) if machine else ()

    print("\nValores de TEMP por maquina:")
    for row in conn.execute(query.format(where=where), params):
        print(f"  {row[0]}: {row[1]} filas, {row[2]} sin valor de TEMP")

def press_summary(conn: sqlite3.Connection, machine: str | None = None) -> None:
    query = """
        SELECT f.machine,
               COUNT(m.id) AS total,
               SUM(CASE WHEN m.pressure_raw IS NULL OR m.pressure_raw = ''
                        THEN 1 ELSE 0 END) AS vacios
        FROM files f
        LEFT JOIN measurements_raw m ON m.file_id = f.id
        {where}
        GROUP BY f.machine
        ORDER BY f.machine
    """
    where = "WHERE f.machine = ?" if machine else ""
    params = (machine,) if machine else ()

    print("\nValores de PRESS por maquina:")
    for row in conn.execute(query.format(where=where), params):
        print(f"  {row[0]}: {row[1]} filas, {row[2]} sin valor de PRESS")

def classify(value: str | None) -> str:
    if value is None or value == "":
        return "vacio"
    if DECIMAL_RE.match(value):
        return "decimal_positivo"
    if value.startswith("-") and DECIMAL_RE.match(value[1:]):
        return "decimal_negativo"
    if ENTERO_RE.match(value):
        return "entero_positivo"
    if value.startswith("-") and ENTERO_RE.match(value[1:]):
        return "entero_negativo"
    return "otro"


# clasifica los valores unicos de una columna (temperature_raw / pressure_raw)
# y cuenta cuantas filas caen en cada categoria: decimal +, decimal -, vacio, otro
def value_patterns(conn: sqlite3.Connection, column: str, machine: str | None = None) -> None:
    query = f"""
        SELECT m.{column}, COUNT(*) AS n
        FROM measurements_raw m
        JOIN files f ON f.id = m.file_id
        {{where}}
        GROUP BY m.{column}
    """
    where = "WHERE f.machine = ?" if machine else ""
    params = (machine,) if machine else ()

    totals: dict[str, int] = {}
    otros: list[tuple[str, int]] = []

    for value, n in conn.execute(query.format(where=where), params):
        categoria = classify(value)
        totals[categoria] = totals.get(categoria, 0) + n
        if categoria == "otro":
            otros.append((value, n))

    categorias = (
        "decimal_positivo",
        "decimal_negativo",
        "entero_positivo",
        "entero_negativo",
        "vacio",
        "otro",
    )
    print(f"\nPatrones de valores en {column}:")
    for categoria in categorias:
        print(f"  {categoria}: {totals.get(categoria, 0)} filas")

    total_filas = conn.execute(
        f"SELECT COUNT(*) FROM measurements_raw m JOIN files f ON f.id = m.file_id {where}",
        params,
    ).fetchone()[0]
    suma_patrones = sum(totals.values())
    estado = "OK" if suma_patrones == total_filas else "DESCUADRE"
    print(f"  total filas: {total_filas}, suma patrones: {suma_patrones} [{estado}]")

    if otros:
        print(f"  valores 'otro' encontrados ({len(otros)} distintos):")
        for value, n in sorted(otros, key=lambda x: -x[1]):
            print(f"    {value!r}: {n} filas")


def main() -> None:
    machine = sys.argv[1] if len(sys.argv) > 1 else None

    conn = sqlite3.connect(DB_PATH)
    try:
        rows_per_file(conn, machine)
        temp_summary(conn, machine)
        press_summary(conn, machine)
        value_patterns(conn, "temperature_raw", machine)
        value_patterns(conn, "pressure_raw", machine)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
