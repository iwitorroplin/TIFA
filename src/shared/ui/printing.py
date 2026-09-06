"""Impresión y exportación a PDF, común a todos los módulos.

Se arma un `PrintJob` con bloques —encabezado, texto, tabla, imagen— y de él
salen los dos caminos que necesita cualquier proceso: la vista previa de
impresión y el PDF. Los dos parten del mismo HTML, así que lo que se imprime y
lo que se guarda nunca se separan.

Por qué HTML sobre un QTextDocument y no un QTableWidget: QTextDocument pagina
solo, así que una tabla de 500 filas sale en tantas páginas como haga falta. Un
QTableWidget se pinta de una vez sobre la página y lo que no cabe se pierde.

La tabla es lo que se imprime casi siempre, y para ese caso están los atajos
`print_table` / `table_to_pdf`. Gráficos e imágenes entran por `add_image`: un
gráfico ya pintado (QPixmap/QImage) se pasa tal cual, sin pasar por disco.
"""

from __future__ import annotations

import datetime as dt
import html
import itertools
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Protocol, Sequence

from PySide6.QtCore import QMarginsF, QStandardPaths, QUrl
from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPixmap, QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PySide6.QtWidgets import QFileDialog, QWidget

# DIN-A4 por defecto: es el papel de las impresoras de planta. Se puede pedir
# otro tamaño con `page_size`, pero nadie debería tener que decirlo.
DEFAULT_PAGE_SIZE = QPageSize.PageSizeId.A4
_DEFAULT_MARGIN_MM = 10.0
_MOMENT_FORMAT = "%d/%m/%Y %H:%M"

# Los estilos van en línea y no en una hoja de estilos: QTextDocument entiende
# solo un subconjunto de CSS, y los atributos y estilos de celda son la parte
# que respeta siempre.
_HEADER_CELL_STYLE = "background-color:#e6e6e6;"
_HIGHLIGHT_CELL_STYLE = "background-color:#fff4c8; color:#5a3c00;"


class Orientation(Enum):
    """Orientación del papel. Una tabla ancha se lee mucho mejor apaisada, así
    que los atajos de tabla usan LANDSCAPE salvo que se pida otra cosa."""

    PORTRAIT = QPageLayout.Orientation.Portrait
    LANDSCAPE = QPageLayout.Orientation.Landscape


class Align(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


# Registra una imagen en el documento y devuelve el nombre con el que el HTML
# puede referenciarla (ver `PrintJob.build_document`).
RegisterImage = Callable[[QImage], str]


class _Block(Protocol):
    def render(self, register_image: RegisterImage) -> str: ...


def _cell(value: object) -> str:
    """Texto listo para meter en el HTML: nunca None y siempre escapado.

    El escapado se centraliza aquí a propósito: quien construye un informe pasa
    datos crudos (nombres de producto, notas de revisión escritas a mano) y no
    tiene por qué acordarse de escaparlos uno a uno.
    """
    return "" if value is None else html.escape(str(value))


@dataclass(frozen=True)
class _Text:
    fragment: str

    def render(self, register_image: RegisterImage) -> str:
        return self.fragment


@dataclass(frozen=True)
class _Table:
    headers: Sequence[str]
    rows: Sequence[Sequence[object]]
    # Una marca por fila: la que va a True se imprime resaltada (por ejemplo los
    # ciclos pendientes de revisión, igual que se ven en pantalla).
    highlighted: Sequence[bool] | None
    aligns: Sequence[Align] | None

    def render(self, register_image: RegisterImage) -> str:
        filas = [self._row_html(self.headers, style=_HEADER_CELL_STYLE, tag="th")]
        for index, row in enumerate(self.rows):
            resaltada = bool(self.highlighted[index]) if self.highlighted else False
            filas.append(self._row_html(row, style=_HIGHLIGHT_CELL_STYLE if resaltada else ""))

        return (
            "<table border='1' cellspacing='0' cellpadding='4' width='100%'>"
            f"{''.join(filas)}"
            "</table>"
        )

    def _row_html(self, values: Sequence[object], *, style: str, tag: str = "td") -> str:
        celdas = "".join(
            f"<{tag} align='{self._align(column)}' style='{style}'>{_cell(value)}</{tag}>"
            for column, value in enumerate(values)
        )
        return f"<tr>{celdas}</tr>"

    def _align(self, column: int) -> str:
        if not self.aligns or column >= len(self.aligns):
            return Align.LEFT.value
        return self.aligns[column].value


@dataclass(frozen=True)
class _Image:
    source: QImage | QPixmap | Path | str
    width_px: int | None
    caption: str | None

    def render(self, register_image: RegisterImage) -> str:
        image = _as_image(self.source)
        if image is None:
            # Que falte una imagen no puede tumbar el informe entero: se deja
            # constancia en el propio papel y lo demás se imprime igual.
            return f"<p><i>[No se pudo cargar la imagen: {_cell(self.source)}]</i></p>"

        width = f" width='{self.width_px}'" if self.width_px else ""
        caption = f"<p><i>{_cell(self.caption)}</i></p>" if self.caption else ""
        return f"<p><img src='{register_image(image)}'{width}></p>{caption}"


def _as_image(source: QImage | QPixmap | Path | str) -> QImage | None:
    if isinstance(source, QImage):
        return source if not source.isNull() else None
    if isinstance(source, QPixmap):
        return source.toImage() if not source.isNull() else None

    image = QImage(str(source))
    return image if not image.isNull() else None


class PrintJob:
    """Un documento a imprimir: se le añaden bloques y luego se manda a la vista
    previa (`preview`) o a un PDF (`export_pdf`).

    Los `add_*` devuelven el propio job para poder encadenarlos.
    """

    def __init__(
        self,
        title: str,
        *,
        subtitle: str | None = None,
        orientation: Orientation = Orientation.PORTRAIT,
        page_size: QPageSize.PageSizeId = DEFAULT_PAGE_SIZE,
        margin_mm: float = _DEFAULT_MARGIN_MM,
        generated_at: dt.datetime | None = None,
    ) -> None:
        self.title = title
        self.subtitle = subtitle
        self.orientation = orientation
        self.page_size = page_size
        self.margin_mm = margin_mm
        # La hora se fija al crear el job, no al renderizar: si del mismo job
        # salen el papel y el PDF, los dos llevan la misma hora de generación.
        self.generated_at = generated_at or dt.datetime.now()
        self._blocks: list[_Block] = []

    def add_heading(self, text: str, level: int = 3) -> "PrintJob":
        return self._add(_Text(f"<h{level}>{_cell(text)}</h{level}>"))

    def add_paragraph(self, text: str) -> "PrintJob":
        return self._add(_Text(f"<p>{_cell(text)}</p>"))

    def add_table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[object]],
        *,
        highlighted: Sequence[bool] | None = None,
        aligns: Sequence[Align] | None = None,
    ) -> "PrintJob":
        return self._add(_Table(
            list(headers),
            [list(row) for row in rows],
            list(highlighted) if highlighted is not None else None,
            list(aligns) if aligns is not None else None,
        ))

    def add_image(
        self,
        source: QImage | QPixmap | Path | str,
        *,
        width_px: int | None = None,
        caption: str | None = None,
    ) -> "PrintJob":
        """Una imagen o un gráfico ya pintado (QPixmap/QImage), o la ruta de un fichero."""
        return self._add(_Image(source, width_px, caption))

    def to_html(self) -> str:
        """El HTML del documento. Las imágenes salen referenciadas por nombre,
        así que solo sirve para depurar o para comprobarlo en un test."""
        nombres = itertools.count()
        return self._html(lambda image: f"tifa-print-image-{next(nombres)}")

    def build_document(self) -> QTextDocument:
        document = QTextDocument()
        contador = itertools.count()

        def register_image(image: QImage) -> str:
            # QTextDocument no resuelve por su cuenta rutas de disco ni data-URI:
            # la imagen se le entrega como recurso con un nombre inventado y el
            # HTML la referencia por ese nombre.
            name = f"tifa-print-image-{next(contador)}"
            document.addResource(QTextDocument.ResourceType.ImageResource, QUrl(name), image)
            return name

        document.setHtml(self._html(register_image))
        return document

    def preview(self, parent: QWidget | None = None) -> None:
        """Abre la vista previa estándar; desde ahí el usuario imprime."""
        document = self.build_document()
        dialog = QPrintPreviewDialog(self._new_printer(), parent)
        dialog.paintRequested.connect(document.print_)
        dialog.exec()

    def export_pdf(self, path: Path | str) -> Path:
        """Escribe el documento en `path` y devuelve la ruta escrita."""
        destino = Path(path)
        destino.parent.mkdir(parents=True, exist_ok=True)

        printer = self._new_printer()
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(destino))
        self.build_document().print_(printer)
        return destino

    def _add(self, block: _Block) -> "PrintJob":
        self._blocks.append(block)
        return self

    def _html(self, register_image: RegisterImage) -> str:
        cuerpo = "".join(block.render(register_image) for block in self._blocks)
        return self._header_html() + cuerpo

    def _header_html(self) -> str:
        partes = [f"Generado: {self.generated_at:{_MOMENT_FORMAT}}"]
        if self.subtitle:
            partes.append(self.subtitle)
        return (
            f"<h2>{_cell(self.title)}</h2>"
            f"<p>{' &middot; '.join(_cell(parte) for parte in partes)}</p>"
        )

    def _new_printer(self) -> QPrinter:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(self.page_size))
        printer.setPageOrientation(self.orientation.value)
        printer.setPageMargins(
            QMarginsF(self.margin_mm, self.margin_mm, self.margin_mm, self.margin_mm),
            QPageLayout.Unit.Millimeter,
        )
        return printer


def table_job(
    title: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[object]],
    *,
    subtitle: str | None = None,
    highlighted: Sequence[bool] | None = None,
    aligns: Sequence[Align] | None = None,
    orientation: Orientation = Orientation.LANDSCAPE,
    page_size: QPageSize.PageSizeId = DEFAULT_PAGE_SIZE,
) -> PrintJob:
    """Un job con una sola tabla: el informe de siempre.

    Devuelve el job en vez de imprimir directamente para que la misma tabla
    pueda ir a la impresora y al PDF sin construirla dos veces.
    """
    job = PrintJob(title, subtitle=subtitle, orientation=orientation, page_size=page_size)
    job.add_table(headers, rows, highlighted=highlighted, aligns=aligns)
    return job


def print_table(
    parent: QWidget | None,
    title: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[object]],
    **options,
) -> None:
    """Vista previa de una tabla; `options` son las de `table_job`."""
    table_job(title, headers, rows, **options).preview(parent)


def table_to_pdf(
    path: Path | str,
    title: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[object]],
    **options,
) -> Path:
    """Una tabla directa a PDF; `options` son las de `table_job`."""
    return table_job(title, headers, rows, **options).export_pdf(path)


def ask_pdf_path(parent: QWidget | None, suggested_name: str) -> Path | None:
    """Diálogo "guardar como" para un PDF. None si el usuario cancela.

    Se propone la carpeta de Documentos del usuario: el directorio de trabajo de
    la app es el del programa, y ahí no debería escribir nadie.
    """
    documentos = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    sugerida = str(Path(documentos) / suggested_name) if documentos else suggested_name

    ruta, _ = QFileDialog.getSaveFileName(parent, "Guardar PDF", sugerida, "PDF (*.pdf)")
    if not ruta:
        return None

    destino = Path(ruta)
    return destino if destino.suffix.lower() == ".pdf" else destino.with_suffix(".pdf")
