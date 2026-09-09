"""Lo que la interfaz (Fase 4) necesita del resto del módulo: la
configuración cargada y un único punto para importar una máquina, abriendo y
cerrando su propia conexión a `tifa.db`.

Sin scheduler ni monitor de disponibilidad -a diferencia de
`src/modules/steriflow/logic/controller.py`-: Ferlo no dispara nada por su
cuenta (D4, decisión tomada: un botón, no vigilancia de carpeta ni
planificador). Por eso este controller no necesita `start()`/`stop()` ni
hilos propios; el hilo de fondo de una importación lo levanta
`tasks/import_runner.py`, no este módulo.
"""

from __future__ import annotations

import datetime as dt

from src.modules.ferlo.logic.analysis import programs as programs_repo
from src.modules.ferlo.logic.analysis import repo as analysis_repo
from src.modules.ferlo.logic.analysis.models import CycleResult, ManualVerdict, SterilizationProgram
from src.modules.ferlo.logic.config import Settings, load_settings
from src.modules.ferlo.logic.ingest.service import ImportSummary, import_machine, reassign_program
from src.modules.ferlo.logic.machines import MACHINES
from src.shared.db.connection import connect


class FerloController:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def reload(self) -> None:
        """Descarta la configuración en memoria y la vuelve a leer de disco
        -tras guardar cambios en la pestaña de Configuración, por ejemplo."""
        self.settings = load_settings()

    @property
    def machines(self) -> tuple[str, ...]:
        return MACHINES

    def import_machine(self, machine: str) -> ImportSummary:
        """Importa y analiza todo lo pendiente de `machine`. Abre su propia
        conexión y la cierra al terminar: se llama desde un hilo de fondo
        (ver `tasks/import_runner.py`), nunca desde el hilo de la interfaz."""
        conn = connect()
        try:
            return import_machine(conn, self.settings, machine)
        finally:
            conn.close()

    # --- lo que necesita el diálogo de detalle (ui/detail_dialog.py) ---

    def list_programs(self, *, include_inactive: bool = True) -> list[SterilizationProgram]:
        conn = connect()
        try:
            return programs_repo.list_programs(conn, include_inactive=include_inactive)
        finally:
            conn.close()

    def reassign_program(
        self, machine: str, started_at: dt.datetime, program_code: int | None
    ) -> CycleResult | None:
        """Asigna o quita el programa de un ciclo ya guardado, y lo reevalúa
        -acto explícito de una persona, ver `logic/ingest/service.py`."""
        conn = connect()
        try:
            return reassign_program(conn, self.settings, machine, started_at, program_code)
        finally:
            conn.close()

    def set_manual_verdict(self, cycle_id: int, verdict: ManualVerdict, notes: str | None) -> None:
        conn = connect()
        try:
            analysis_repo.set_manual_verdict(conn, cycle_id, verdict, notes)
        finally:
            conn.close()

    def upsert_program(self, program: SterilizationProgram) -> None:
        conn = connect()
        try:
            programs_repo.upsert_program(conn, program)
        finally:
            conn.close()

    def set_program_active(self, code: int, active: bool) -> None:
        conn = connect()
        try:
            programs_repo.set_program_active(conn, code, active)
        finally:
            conn.close()


def build_default_controller() -> FerloController:
    # load_settings() ya llama a ensure_config_file() por dentro -crea
    # `ferloConfig.yaml` desde el default si es el primer arranque-, igual
    # que build_default_controller() de Steriflow.
    return FerloController(load_settings())
