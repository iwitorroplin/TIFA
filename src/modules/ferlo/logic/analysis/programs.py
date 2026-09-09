"""Programas de consigna de la planta -tabla `ferlo_program`.

El origen (`sterilization_analysis`) apuntaba esta tabla a un Excel de la
planta (`Programas Ferlo.xlsx`, ver `core/config.py:programs_source`), pero
ni ese fichero ni el código que lo parseaba llegaron a este repo -solo la
referencia a la ruta-. No hay nada que portar aquí, así que en su lugar la
tabla se gestiona a mano desde la pestaña de Configuración (Fase 4):
`list_programs`/`upsert_program` son la interfaz que usaría un importador de
Excel el día que aparezca, así que añadirlo entonces es una función más en
este módulo, no un cambio de forma.

Los programas nunca se borran, solo se desactivan (`is_active=0`): el código
de programa tiene que seguir señalando la misma posición real del autoclave
-un programa "sin datos" de hoy puede volver a usarse mañana, y un `DELETE`
dejaría huérfanos los ciclos ya guardados que lo referencian (FK de
`ferlo_cycle.program_code`, ver `logic/schema.py`)-.
"""

from __future__ import annotations

import sqlite3

from .models import SterilizationProgram
from .repo import program_from_row


def list_programs(conn: sqlite3.Connection, *, include_inactive: bool = True) -> list[SterilizationProgram]:
    query = "SELECT code, name, target_temperature_c, target_time_min, is_active FROM ferlo_program"
    if not include_inactive:
        query += " WHERE is_active = 1"
    query += " ORDER BY code"
    return [program_from_row(fila) for fila in conn.execute(query).fetchall()]


def upsert_program(conn: sqlite3.Connection, program: SterilizationProgram) -> None:
    """Crea el programa si su código no existe, o actualiza sus datos si ya
    existía -nunca lo borra, ver el docstring de este módulo."""
    conn.execute(
        "INSERT INTO ferlo_program (code, name, target_temperature_c, target_time_min, is_active)"
        " VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT(code) DO UPDATE SET"
        " name = excluded.name,"
        " target_temperature_c = excluded.target_temperature_c,"
        " target_time_min = excluded.target_time_min,"
        " is_active = excluded.is_active",
        (
            program.code, program.name, program.target_temperature_c,
            program.target_time_min, int(program.is_active),
        ),
    )
    conn.commit()


def set_program_active(conn: sqlite3.Connection, code: int, active: bool) -> None:
    conn.execute("UPDATE ferlo_program SET is_active = ? WHERE code = ?", (int(active), code))
    conn.commit()


def suggest_programs(
    programs: list[SterilizationProgram],
    measured_setpoint_c: float,
    *,
    tolerance_c: float = 2.0,
) -> list[SterilizationProgram]:
    """Candidatos cuya consigna cae a menos de `tolerance_c` de la consigna
    medida del ciclo, del más cercano al más lejano.

    Con ~38 programas y varios compartiendo exactamente temperatura y tiempo
    (ver el plan de la Fase 4, invariante "importar nunca asigna programa"),
    esto reduce a 2-4 candidatos: sugiere, no elige -la asignación sigue
    siendo siempre un acto explícito de quien usa la pantalla.
    """
    activos = [p for p in programs if p.is_active]
    cercanos = [p for p in activos if abs(p.target_temperature_c - measured_setpoint_c) <= tolerance_c]
    return sorted(cercanos, key=lambda p: abs(p.target_temperature_c - measured_setpoint_c))
