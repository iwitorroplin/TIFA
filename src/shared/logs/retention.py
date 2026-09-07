"""Limpieza de logs viejos.

Los logs son el historial de la aplicación (pestaña Logs del navbar), así que
no se pueden borrar a la ligera... pero tampoco pueden crecer para siempre:
cada ejecución de backup deja su propio fichero y hay varias al día, así que en
un par de años son miles de ficheros que además hay que releer del disco cada
vez que se abre la pestaña.

La antigüedad a partir de la cual se borra es un dato de configuración
(`logs.retentionMonths` en appConfig, editable en la pestaña Configuración),
no una constante escondida aquí: cuánto historial hay que guardar es una
decisión de quien usa la app, no del programa.
"""

from __future__ import annotations

import calendar
from datetime import datetime
from pathlib import Path


def cutoff_date(months: int, now: datetime | None = None) -> datetime:
    """La fecha a partir de la cual un log se considera viejo.

    Resta meses de calendario de verdad (no bloques de 30 días): "12 meses"
    tiene que significar el mismo día del año pasado, que es lo que entiende
    quien configura la retención. El día se recorta al último del mes destino
    para que un 31 de marzo menos un mes sea el 28 (o 29) de febrero.
    """
    now = now or datetime.now()

    total = now.month - 1 - months
    year = now.year + total // 12
    month = total % 12 + 1
    day = min(now.day, calendar.monthrange(year, month)[1])

    return now.replace(year=year, month=month, day=day)


def purge_old_logs(directory: Path, months: int, now: datetime | None = None) -> tuple[int, int]:
    """Borra los `*.log` de `directory` más viejos que `months` meses.

    Devuelve (borrados, no_borrados). `months <= 0` desactiva la limpieza y no
    borra nada: es la forma de decir "guarda el historial entero".

    Se mira la fecha de modificación y no el nombre: los ficheros de backup
    llevan la fecha en el nombre, pero el log del agente y los de otros módulos
    no, y esto tiene que valer para todos.
    """
    if months <= 0:
        return (0, 0)

    cutoff = cutoff_date(months, now).timestamp()

    try:
        entries = list(directory.glob("*.log"))
    except OSError:
        return (0, 0)

    borrados = 0
    fallidos = 0
    for entry in entries:
        try:
            if entry.stat().st_mtime >= cutoff:
                continue
            entry.unlink()
            borrados += 1
        except OSError:
            # Fichero abierto por otro proceso, permisos, unidad de red que se
            # cayó... No es motivo para abortar la limpieza del resto: se
            # cuenta y el que llama lo deja dicho en el log.
            fallidos += 1

    return (borrados, fallidos)
