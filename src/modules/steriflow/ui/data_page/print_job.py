from src.modules.steriflow.logic.sterilization.columns import Align as ColumnAlign
from src.shared.ui import printing

# Traduce el Align propio del dominio (logic/sterilization/columns.py, que no
# puede importar Qt) al Align de printing.py que sí lo hace.
_PRINT_ALIGN_BY_COLUMN_ALIGN = {
    ColumnAlign.LEFT: printing.Align.LEFT,
    ColumnAlign.CENTER: printing.Align.CENTER,
    ColumnAlign.RIGHT: printing.Align.RIGHT,
}

PRINT_TITLE = "Ciclos de esterilización — Steriflow"
PRINT_PDF_PREFIX = "ciclos_esterilizacion"


def build_print_job(view_model, cycles) -> printing.PrintJob:
    """La tabla de la selección, lista tanto para la impresora como para el
    PDF. Mismas columnas que la pantalla -misma `visible_columns()`-, así que
    nunca hay un conjunto de columnas "solo para imprimir"."""
    columns = view_model.visible_columns()
    headers = [col.header for col in columns]
    aligns = [_PRINT_ALIGN_BY_COLUMN_ALIGN[col.align] for col in columns]
    return printing.table_job(
        PRINT_TITLE,
        headers,
        [view_model.print_cells(cycle) for cycle in cycles],
        subtitle=f"{len(cycles)} ciclo(s)",
        # Los pendientes de revisión salen resaltados en papel igual que en pantalla.
        highlighted=[cycle.needs_review for cycle in cycles],
        aligns=aligns,
    )
