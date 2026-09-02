"""Panel de Steriflow: la pestana entera.

Autosuficiente a proposito -tabla, filtro por autoclave e importacion propias-,
para que la ventana principal solo tenga que colgarlo de una pestana y no
mezclarlo con nada de Ferlo.
"""

from __future__ import annotations

import sqlite3
import threading
import time

from PySide6.QtCore import QModelIndex, QObject, QSortFilterProxyModel, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...core.config import Settings
from ...ui.task_runner import TaskRunner
from .. import repo
from ..jobs import import_reports_job
from ..repo import SteriflowCycleRow
from ..schema import ensure_tables
from ..service import report_path
from .table_model import COL_ID, SteriflowTableModel

# Cada cuanto se refresca la barra durante la importacion.
_MS_ENTRE_AVISOS = 100.0

# A partir de aqui se pregunta antes de abrir: cada informe sale en su propia
# ventana del visor del sistema, y una seleccion de tres pantallas de tabla deja
# el escritorio inservible.
_ABRIR_SIN_PREGUNTAR = 10


class _Progreso(QObject):
    """Puente de hilo para el avance de la importacion.

    Vive en el hilo de la interfaz; el hilo de fondo llama a `avance.emit`, y Qt
    entrega la senal al slot por cola, que es la unica forma segura de tocar
    widgets desde otro hilo.
    """

    avance = Signal(int, int, str)


def _espaciado(fn, ms: float = _MS_ENTRE_AVISOS):
    """Envuelve `fn` para que no se llame mas de una vez cada `ms`.

    El filtro va en el hilo de fondo, antes de emitir, y no despues: saltarse
    2.000 informes ya importados tarda 0,1 s, y emitir 2.000 senales en ese rato
    inunda la cola de eventos de la ventana para pintar avisos que nadie llega a
    leer. El ultimo siempre pasa, para que la barra acabe en el total.
    """
    ultimo = [0.0]

    def envolver(hechos: int, total: int, etiqueta: str) -> None:
        ahora = time.monotonic()
        if hechos >= total or (ahora - ultimo[0]) * 1000.0 >= ms:
            ultimo[0] = ahora
            fn(hechos, total, etiqueta)

    return envolver


class SteriflowPanel(QWidget):
    def __init__(
        self, conn: sqlite3.Connection, settings: Settings, parent=None
    ) -> None:
        super().__init__(parent)
        self.conn = conn
        self.settings = settings
        ensure_tables(self.conn)
        self._tareas = TaskRunner(self)
        self._cancelar: threading.Event | None = None
        self._progreso: _Progreso | None = None

        self._construir_ui()
        self.refresh()

    # ------------------------------------------------------------------ UI

    def _construir_ui(self) -> None:
        self._combo_autoclave = QComboBox()
        self._combo_autoclave.currentIndexChanged.connect(self.refresh)

        self._boton_importar = QPushButton("Importar informes")
        self._boton_importar.clicked.connect(self._on_importar)
        boton_actualizar = QPushButton("Actualizar")
        boton_actualizar.clicked.connect(self.refresh)

        self._boton_abrir = QPushButton("Abrir PDF")
        self._boton_abrir.setEnabled(False)
        self._boton_abrir.setToolTip(
            "Abre en el visor del sistema los informes de las filas "
            "seleccionadas (doble clic sobre una fila abre el suyo)."
        )
        self._boton_abrir.clicked.connect(self._on_abrir)

        self._etiqueta_ruta = QLabel()
        self._etiqueta_ruta.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        cabecera = QHBoxLayout()
        cabecera.addWidget(QLabel("Autoclave:"))
        cabecera.addWidget(self._combo_autoclave)
        cabecera.addWidget(self._boton_importar)
        cabecera.addWidget(boton_actualizar)
        cabecera.addWidget(self._boton_abrir)
        cabecera.addStretch()
        cabecera.addWidget(self._etiqueta_ruta)

        self._modelo = SteriflowTableModel(self)
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._modelo)
        # El orden compara el valor nativo que devuelve `EditRole`, no el texto
        # ya formateado (ver el docstring de `table_model`).
        self._proxy.setSortRole(Qt.ItemDataRole.EditRole)

        self._tabla = QTableView()
        self._tabla.setModel(self._proxy)
        self._tabla.setSortingEnabled(True)
        self._tabla.sortByColumn(COL_ID, Qt.SortOrder.DescendingOrder)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tabla.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._tabla.doubleClicked.connect(self._on_doble_clic)
        self._tabla.selectionModel().selectionChanged.connect(self._on_seleccion)

        self._etiqueta_estado = QLabel()

        # Fila de progreso, oculta salvo mientras se importa. Leer 2.000
        # informes por primera vez son ~11 minutos: sin esto la unica senal de
        # que la aplicacion sigue viva seria que no responde.
        self._barra = QProgressBar()
        self._barra.setTextVisible(True)
        self._boton_cancelar = QPushButton("Cancelar")
        self._boton_cancelar.clicked.connect(self._on_cancelar)
        self._fila_progreso = QWidget()
        fila = QHBoxLayout(self._fila_progreso)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.addWidget(self._barra, stretch=1)
        fila.addWidget(self._boton_cancelar)
        self._fila_progreso.setVisible(False)

        layout = QVBoxLayout(self)
        layout.addLayout(cabecera)
        layout.addWidget(self._tabla)
        layout.addWidget(self._fila_progreso)
        layout.addWidget(self._etiqueta_estado)

    # -------------------------------------------------------------- listado

    def refresh(self) -> None:
        """Recarga los ciclos guardados desde la base de datos."""
        self._recargar_autoclaves()
        codigo = self._combo_autoclave.currentData()
        ciclos = repo.list_cycles(self.conn, autoclave_code=codigo)
        nombres = {a.code: a.name for a in self.settings.steriflow_autoclaves}
        self._modelo.set_cycles(ciclos, autoclave_names=nombres)

        raiz = self.settings.steriflow_reports_root
        self._etiqueta_ruta.setText(f"Informes: {raiz}")
        self._etiqueta_ruta.setToolTip(
            "Carpeta raiz de informes. Se cambia en Configuracion → Steriflow."
        )
        sin_fase = sum(1 for c in ciclos if c.sterilization is None)
        texto = f"{len(ciclos)} ciclos"
        if sin_fase:
            texto += f"  ({sin_fase} sin fase de esterilizacion)"
        self._etiqueta_estado.setText(texto)
        # Recargar la tabla vacia la seleccion sin pasar por `selectionChanged`.
        self._on_seleccion()

    def _recargar_autoclaves(self) -> None:
        """Rellena el combo conservando la seleccion actual.

        Se bloquean las senales porque `clear()` dispara
        `currentIndexChanged`, y ese slot es `refresh()`: sin el bloqueo, cada
        recarga se llamaria a si misma.
        """
        combo = self._combo_autoclave
        anterior = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Todos", None)
        for autoclave in self.settings.steriflow_autoclaves:
            combo.addItem(autoclave.name, autoclave.code)
        indice = combo.findData(anterior)
        combo.setCurrentIndex(indice if indice >= 0 else 0)
        combo.blockSignals(False)

    # ---------------------------------------------------------- abrir el PDF

    def _ciclos_seleccionados(self) -> list[SteriflowCycleRow]:
        """Los ciclos de las filas seleccionadas, en el orden en que se ven.

        Se ordena por la fila del proxy y no por la del modelo: lo que abre el
        boton debe salir en el mismo orden que tiene la tabla delante, sea cual
        sea la columna por la que este ordenada.
        """
        indices = self._tabla.selectionModel().selectedRows()
        ciclos = []
        for indice in sorted(indices, key=lambda i: i.row()):
            ciclo = self._modelo.cycle_at(self._proxy.mapToSource(indice).row())
            if ciclo is not None:
                ciclos.append(ciclo)
        return ciclos

    def _on_seleccion(self, *_) -> None:
        self._boton_abrir.setEnabled(bool(self._tabla.selectionModel().hasSelection()))

    def _on_doble_clic(self, indice: QModelIndex) -> None:
        ciclo = self._modelo.cycle_at(self._proxy.mapToSource(indice).row())
        if ciclo is not None:
            self._abrir([ciclo])

    def _on_abrir(self) -> None:
        self._abrir(self._ciclos_seleccionados())

    def _abrir(self, ciclos: list[SteriflowCycleRow]) -> None:
        """Abre cada informe en el visor de PDF del sistema."""
        if not ciclos:
            return
        if len(ciclos) > _ABRIR_SIN_PREGUNTAR:
            respuesta = QMessageBox.question(
                self, "Abrir informes",
                f"Se van a abrir {len(ciclos)} informes, cada uno en su propia "
                f"ventana del visor de PDF.\n\n¿Continuar?",
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return

        fallos = []
        for ciclo in ciclos:
            # Se resuelve uno a uno, y no de golpe antes de abrir nada, para que
            # un informe que ya no este no impida abrir los demas.
            ruta = report_path(self.settings, ciclo)
            if ruta is None:
                fallos.append(f"{ciclo.source_filename}: no se encuentra el fichero")
            elif not QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta))):
                fallos.append(f"{ciclo.source_filename}: el sistema no pudo abrirlo")

        if fallos:
            self._avisar_de_fallos(fallos, len(ciclos))

    def _avisar_de_fallos(self, fallos: list[str], intentados: int) -> None:
        mostrar = fallos[:10]
        mensaje = f"{len(fallos)} de {intentados} informes no se han podido abrir:\n"
        mensaje += "\n".join(mostrar)
        if len(fallos) > len(mostrar):
            mensaje += f"\n… y {len(fallos) - len(mostrar)} mas"
        # De cada ciclo solo se guarda el nombre del fichero: si la carpeta ya no
        # es la de entonces, el PDF no aparece aunque el ciclo siga en la tabla.
        mensaje += (
            f"\n\nLos informes se buscan en la carpeta de cada autoclave, bajo "
            f"{self.settings.steriflow_reports_root}. La ruta se cambia en "
            f"Configuracion → Steriflow."
        )
        QMessageBox.warning(self, "Abrir informes", mensaje)

    # ------------------------------------------------------------ importar

    def _on_importar(self) -> None:
        self._boton_importar.setEnabled(False)
        self._etiqueta_estado.setText("Buscando informes…")

        self._cancelar = threading.Event()
        self._progreso = _Progreso()
        self._progreso.avance.connect(self._on_avance)

        self._barra.setRange(0, 0)  # indeterminada hasta saber el total
        self._barra.setFormat("")
        self._boton_cancelar.setEnabled(True)
        self._fila_progreso.setVisible(True)

        worker = self._tareas.launch(
            import_reports_job,
            self.settings,
            False,
            _espaciado(self._progreso.avance.emit),
            self._cancelar.is_set,
        )
        worker.finished.connect(self._on_importado)
        worker.failed.connect(self._on_error)

    def _on_avance(self, hechos: int, total: int, etiqueta: str) -> None:
        if self._barra.maximum() != total:
            self._barra.setRange(0, total)
        self._barra.setValue(hechos)
        self._barra.setFormat(f"%v/%m  ({total and hechos * 100 // total}%)")
        self._etiqueta_estado.setText(etiqueta)

    def _on_cancelar(self) -> None:
        if self._cancelar is not None:
            self._cancelar.set()
        self._boton_cancelar.setEnabled(False)
        self._etiqueta_estado.setText("Cancelando…")

    def _terminar_progreso(self) -> None:
        self._fila_progreso.setVisible(False)
        self._boton_importar.setEnabled(True)
        self._cancelar = None
        self._progreso = None

    def _on_importado(self, resultados: list) -> None:
        cancelado = any(r.cancelled for r in resultados)
        self._terminar_progreso()
        if not resultados:
            QMessageBox.information(
                self, "Importar Steriflow",
                "No hay ningun autoclave Steriflow activo en la configuracion.",
            )
            self.refresh()
            return

        lineas = []
        errores = []
        for r in resultados:
            if r.folder_missing:
                lineas.append(f"{r.autoclave.name}: carpeta no encontrada ({r.folder})")
                continue
            partes = [f"{r.cycles_new} nuevos"]
            if r.cycles_updated:
                partes.append(f"{r.cycles_updated} actualizados")
            if r.skipped:
                partes.append(f"{r.skipped} ya importados")
            lineas.append(f"{r.autoclave.name}: " + ", ".join(partes))
            errores.extend(r.errors)

        self.refresh()
        mensaje = "\n".join(lineas)
        if cancelado:
            # Lo ya importado se queda: cada ciclo se confirma por separado, asi
            # que cancelar no deshace nada y reanudar solo lee lo que falta.
            mensaje = (
                "Importacion cancelada. Lo leido hasta ahora se ha guardado; "
                "volver a importar continua donde se dejo.\n\n" + mensaje
            )
        if errores:
            # Los ficheros ilegibles no cancelan la importacion, pero tampoco se
            # silencian: un PDF que no se pudo leer es un ciclo que no esta.
            mostrar = errores[:10]
            mensaje += f"\n\n{len(errores)} ficheros con error:\n" + "\n".join(mostrar)
            if len(errores) > len(mostrar):
                mensaje += f"\n… y {len(errores) - len(mostrar)} mas"
            QMessageBox.warning(self, "Importar Steriflow", mensaje)
        else:
            QMessageBox.information(self, "Importar Steriflow", mensaje)

    def _on_error(self, mensaje: str) -> None:
        self._terminar_progreso()
        self._etiqueta_estado.clear()
        QMessageBox.critical(self, "Error al importar Steriflow", mensaje)
