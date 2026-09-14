"""Qué hay esperando en la entrada, sin tocar nada.

El equivalente al `check` de Steriflow (`logic/backup/availability.py`): mira
antes de mover, para que pulsar Importar no sea la única forma de enterarse de
si había algo. Solo lectura -ni borra de la entrada, ni escribe en
`ferlo_import`, ni funde mensuales-: eso es cosa de `service.py`.

Clasifica cada CSV de `entrada/<machine>/` en nuevo o ya llegado con el mismo
criterio que usará la importación (sha256 en `ferlo_import`, ver `repo.py`),
de modo que lo que se anuncia aquí es exactamente lo que hará el siguiente
Importar, no una estimación aparte.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from src.modules.ferlo.logic.config import Settings

from . import repo


@dataclass(slots=True)
class MachinePending:
    machine: str
    new_files: list[str] = field(default_factory=list)
    already_arrived: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.new_files) + len(self.already_arrived)

    @property
    def has_new(self) -> bool:
        return bool(self.new_files)


@dataclass(slots=True)
class PendingReport:
    machines: list[MachinePending] = field(default_factory=list)

    @property
    def total_new(self) -> int:
        return sum(len(m.new_files) for m in self.machines)

    @property
    def total_already_arrived(self) -> int:
        return sum(len(m.already_arrived) for m in self.machines)

    @property
    def machines_with_new(self) -> list[str]:
        return [m.machine for m in self.machines if m.has_new]


def scan_machine(conn: sqlite3.Connection, settings: Settings, machine: str) -> MachinePending:
    resultado = MachinePending(machine=machine)
    entrada_dir = settings.entrada_dir / machine
    if not entrada_dir.exists():
        return resultado

    for csv_path in sorted(entrada_dir.glob("*.csv")):
        if repo.already_arrived(conn, machine, repo.sha256_of(csv_path)):
            resultado.already_arrived.append(csv_path.name)
        else:
            resultado.new_files.append(csv_path.name)
    return resultado


def scan(conn: sqlite3.Connection, settings: Settings, machines: tuple[str, ...]) -> PendingReport:
    return PendingReport(machines=[scan_machine(conn, settings, m) for m in machines])
