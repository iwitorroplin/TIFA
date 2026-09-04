from __future__ import annotations

import subprocess
from enum import Enum

_PING_TIMEOUT_MS = 2000


class MachineStatus(Enum):
    """Resultado de comprobar una IP. Ver `check_machine_status`."""

    ONLINE = "online"
    # El propio router respondió "destino inaccesible": no hay ningún
    # dispositivo respondiendo en esa IP, lo más probable es que esté
    # apagada o desconectada de la red.
    OFFLINE = "offline"
    # Ni eco ni "inaccesible": no se sabe por qué (firewall, cable, la propia
    # red local...), no se puede asumir que la máquina esté apagada.
    CONNECTION_ERROR = "connection_error"


def check_machine_status(ip_address: str) -> MachineStatus:
    """Ping de una sola vez, distinguiendo por qué no responde.

    No basta con `returncode == 0`: si un router intermedio no sabe llegar al
    destino, responde "Host de destino inaccesible" — ping.exe lo cuenta como
    "recibido" (0% perdidos) y sale con código 0 igualmente, aunque la
    máquina real sea inalcanzable. Un eco de verdad siempre trae "TTL=" en la
    salida (esa parte no se traduce ni en el Windows en español); un mensaje
    de error de un router no.
    """
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", str(_PING_TIMEOUT_MS), ip_address],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
            text=True,
            errors="replace",
        )
    except OSError:
        return MachineStatus.CONNECTION_ERROR

    output = result.stdout.upper()
    if result.returncode == 0 and "TTL=" in output:
        return MachineStatus.ONLINE
    if "INACCESIBLE" in output or "UNREACHABLE" in output:
        return MachineStatus.OFFLINE
    return MachineStatus.CONNECTION_ERROR


def is_reachable(ip_address: str) -> bool:
    return check_machine_status(ip_address) == MachineStatus.ONLINE
