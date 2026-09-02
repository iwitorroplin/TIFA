from __future__ import annotations

import subprocess

_PING_TIMEOUT_MS = 2000


def is_reachable(ip_address: str) -> bool:
    """Ping de una sola vez: True solo si llega un eco real de la propia IP.

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
        return result.returncode == 0 and "TTL=" in result.stdout.upper()
    except OSError:
        return False
