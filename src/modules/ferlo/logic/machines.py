"""Las cinco autoclaves Ferlo de la planta.

Único sitio que enumera "F1".."F5": lo usaba solo `logic/ingest/cli.py`
(Fase 1); la Fase 4 le añade el selector de máquina de la pestaña de
Importación y los filtros de la pestaña de Ciclos, y todos comparten esta
misma lista en vez de repetirla.
"""

from __future__ import annotations

MACHINES: tuple[str, ...] = ("F1", "F2", "F3", "F4", "F5")
