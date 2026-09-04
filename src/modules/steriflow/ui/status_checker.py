from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal

from src.modules.steriflow.logic.network import MachineStatus, check_machine_status


class AutoclaveStatusChecker(QObject):
    """Hace ping a cada IP en su propio hilo (hasta 2 s por máquina, ver
    check_machine_status) para no congelar la interfaz, y avisa por señal
    según van llegando los resultados — Qt entrega la señal ya en el hilo de
    la interfaz, así que el slot conectado puede tocar widgets sin problema.
    """

    checked = Signal(str, MachineStatus)

    def check(self, name_ip_pairs) -> None:
        for name, ip in name_ip_pairs:
            threading.Thread(target=self._check_one, args=(name, ip), daemon=True).start()

    def _check_one(self, name, ip) -> None:
        self.checked.emit(name, check_machine_status(ip))
