"""Carga los programas de consigna de la planta en `ferlo_program`.

Es el importador que `logic/analysis/programs.py` da por venir en su
docstring: el Excel del origen (`Programas Ferlo.xlsx`) nunca llegó a este
repo, así que la fuente aquí es la tabla de `programas_ferlo.md`, transcrita
abajo en `PROGRAMAS`.

Va por `upsert_program` y no por INSERT propio a posta: así pasa por la misma
puerta que la pestaña de Configuración y no hay dos sitios que sepan escribir
en esta tabla.

Idempotente: re-ejecutarlo deja la tabla igual, no duplica. Un código que ya
exista se SOBRESCRIBE con lo que diga este fichero -es la fuente de verdad-,
así que si alguien ajustó un programa a mano desde la app, esto lo pisa.

Los 13 códigos sin datos de la tabla original (3, 5, 6, 16...) se crean
igualmente, desactivados (`is_active=0`) y a 0. El código de programa señala
una posición real del autoclave: reservarla la deja visible en Configuración
para rellenarla el día que se use, en vez de dejar un hueco que nadie sabe si
es un olvido -y encaja con la regla del módulo de no borrar nunca, solo
desactivar-.

Uso: python tools/seed_ferlo_programs.py [--yes]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.modules.ferlo.logic.analysis.models import SterilizationProgram  # noqa: E402
from src.modules.ferlo.logic.analysis.programs import upsert_program  # noqa: E402
from src.shared.db.connection import connect  # noqa: E402

# Base de datos en producción (dentro del ejecutable empaquetado en dist/).
DB_PATH = Path(r"C:\Users\scadaferlo\dev\TIFA\dist\TIFA-0.2.3\data\tifa.db")

# (código, nombre, formato, tiempo consigna en min, temperatura en ºC).
# Copiado de `programas_ferlo.md`; los códigos que allí están en blanco
# aparecen aquí con nombre vacío y se dan de alta desactivados.
PROGRAMAS: tuple[tuple[int, str, str, float, float], ...] = (
    (1, "Ratatouille 5-3 kg", "5-3 kg", 73, 117),
    (2, "Ratatouille 1 kg", "1 kg", 39, 110),
    (3, "", "", 0, 0),
    (4, "Ratatouille 1/2 kg", "1/2 kg", 23, 110),
    (5, "", "", 0, 0),
    (6, "", "", 0, 0),
    (7, "Fritada 1/2 kg", "1/2 kg", 40, 110),
    (8, "Puerro 3 kg", "3 kg", 41, 110),
    (9, "Puerro 1 kg", "1 kg", 32, 110),
    (10, "Tomate Entero BIO 580 ml", "580 ml", 30, 115),
    (11, "Tomate Entero 1 kg", "1 kg", 40, 115),
    (12, "Taboule 5 kg", "5 kg", 80, 110),
    (13, "Ratatouille BIO 580 ml", "580 ml", 30, 110),
    (14, "Taboule 1/2 kg", "1/2 kg", 33, 105),
    (15, "Taboule 3/4 kg", "3/4 kg", 44, 105),
    (16, "", "", 0, 0),
    (17, "", "", 0, 0),
    (18, "Guisante 370 ml", "370 ml", 10, 130),
    (19, "", "", 0, 0),
    (20, "Legumes Cuisines 580 ml", "580 ml", 40, 120),
    (21, "Legumes Soleil 1/2 kg", "1/2 kg", 42, 110),
    (22, "Legumes Pistou 1/2 kg", "1/2 kg", 45, 115),
    (23, "Piperrade BIO 5 kg", "5 kg", 73, 117),
    (24, "", "", 0, 0),
    (25, "Legumes Soleil 3 kg", "3 kg", 73, 117),
    (26, "Legumes Soleil Italie 1/4 kg", "1/4 kg", 30, 110),
    (27, "Soleil Italie 1 kg", "1 kg", 40, 120),
    (28, "Tomate Entero 1/2 kg", "1/2 kg", 13, 115),
    (29, "legumes Soleil 1/2 kg", "1/2 kg", 40, 110),
    (30, "Legumes Gusteua 425 ml", "425 ml", 35, 110),
    (31, "Legumes Cuisines 580 ml", "580 ml", 35, 120),
    (32, "Cebolla Prefrita 1/2 kg", "1/2 kg", 52, 110),
    (33, "Cebolla Prefrita 3 kg", "3 kg", 73, 117),
    (34, "Salade RHD 3 kg", "3 kg", 73, 120),
    (35, "Fritada BA 1 kg", "1 kg", 45, 110),
    (36, "Piperrade 3 kg", "3 kg", 61, 117),
    (37, "Fonds Garniture 3 kg", "3 kg", 60, 117),
    (38, "", "", 0, 0),
    (39, "", "", 0, 0),
    (40, "", "", 0, 0),
    (41, "Legumes Soleil 3 kg", "3 kg", 90, 110),
    (42, "Taboule 5 Legumes 1/2 kg", "1/2 kg", 43, 105),
    (43, "Fritada 3 kg", "3 kg", 61, 117),
    (44, "", "", 0, 0),
    (45, "", "", 0, 0),
    (46, "Ratatouille BIO 720 ml", "720 ml", 35, 110),
    (47, "Guisante 1/6 kg", "1/6 kg", 9, 130),
    (48, "Maiz 1/8 kg", "1/8 kg", 9, 129),
    (49, "Guisante 1/2 kg", "1/2 kg", 12, 130),
    (50, "Guisante 1/4 kg", "1/4 kg", 11, 130),
)


def _confirmar() -> bool:
    if "--yes" in sys.argv:
        return True
    con_datos = sum(1 for _, nombre, *_ in PROGRAMAS if nombre)
    print(f"Base de datos: {DB_PATH}")
    print(
        f"Se van a escribir {len(PROGRAMAS)} programas "
        f"({con_datos} activos, {len(PROGRAMAS) - con_datos} sin datos y desactivados)."
    )
    print("Los códigos que ya existan se sobrescriben.")
    return input("¿Continuar? [s/N] ").strip().lower() in {"s", "si", "sí"}


def main() -> int:
    if not _confirmar():
        print("Cancelado.")
        return 1

    conn = connect(DB_PATH)
    try:
        for codigo, nombre, formato, tiempo, temperatura in PROGRAMAS:
            upsert_program(
                conn,
                SterilizationProgram(
                    code=codigo,
                    name=nombre,
                    format=formato,
                    target_temperature_c=float(temperatura),
                    target_time_min=float(tiempo),
                    # Un código sin nombre no es un programa utilizable
                    # todavía: existe para reservar la posición.
                    is_active=bool(nombre),
                ),
            )
    finally:
        conn.close()

    activos = sum(1 for _, nombre, *_ in PROGRAMAS if nombre)
    print(f"Listo: {len(PROGRAMAS)} programas escritos ({activos} activos).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
