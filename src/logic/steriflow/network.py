from __future__ import annotations

import subprocess

_PING_TIMEOUT_MS = 2000


def is_reachable(ip_address: str) -> bool:
    """Ping de una sola vez: True si la máquina responde en la red."""
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", str(_PING_TIMEOUT_MS), ip_address],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.returncode == 0
    except OSError:
        return False
