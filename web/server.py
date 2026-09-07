"""Servidor de la parte web de TIFA.

Envuelve Uvicorn con la misma API de arranque/parada (`start`/`stop`/
`wait_forever`/`url`) que antes tenía el servidor sobre `http.server`, para
que ni `run_web.py` ni un futuro interruptor en la UI de TIFA tengan que
cambiar cuando cambie el motor de dentro -y de hecho no cambiaron al
sustituirlo.

Sin autenticación ni HTTPS: cualquiera en la red local puede leer y escribir.
Decisión consciente para este alcance, mitigable sin código acotando el
firewall a la subred de la planta.
"""

from __future__ import annotations

import socket
import threading
from typing import Callable

import uvicorn

from web.app import create_app
from web.config import HOST, PORT


def _lan_ip() -> str:
    """IP con la que este PC sale a la red local, para poder decírsela a quien
    vaya a conectarse desde otro ordenador.

    El socket UDP no manda ni un byte -no hace falta que el destino exista-,
    solo obliga al sistema operativo a elegir la interfaz de salida, que es
    justo la que ven los demás PC de la LAN. `gethostbyname(gethostname())`
    no vale: en un PC con VPN, Docker o WSL suele devolver la tarjeta virtual
    equivocada.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("10.255.255.255", 1))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


class _Servidor(uvicorn.Server):
    """Uvicorn intenta instalar manejadores de señal (Ctrl+C) al arrancar,
    pero eso solo funciona en el hilo principal -y este servidor siempre
    corre en un hilo daemon aparte (ver `TifaWebServer.start()`). Se
    desactiva aquí; el propio Ctrl+C lo atiende `wait_forever()`."""

    def install_signal_handlers(self) -> None:
        pass


class TifaWebServer:
    """API de arranque/parada del servidor. `start()`/`stop()` no bloquean
    (salvo el `join` con límite de `stop()`), así que la misma clase sirve
    tanto para `run_web.py` (bloquea después con `wait_forever()`) como para
    un futuro interruptor en la UI de TIFA (un hilo daemon, `start()` y ya).
    """

    def __init__(self, host: str = HOST, port: int = PORT, log: Callable[[str], None] = print) -> None:
        self._host = host
        self._port = port
        self._log = log
        self._servidor: _Servidor | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._servidor is not None

    @property
    def url(self) -> str:
        ip = _lan_ip() if self._host == "0.0.0.0" else self._host
        return f"http://{ip}:{self._port}"

    def start(self) -> None:
        """Levanta el servidor en un hilo daemon y vuelve en cuanto el socket
        ya escucha (o lanza si no pudo arrancar). Idempotente: llamar dos
        veces no abre un segundo socket.
        """
        if self._servidor is not None:
            return
        self._stop_event.clear()
        config = uvicorn.Config(
            create_app(), host=self._host, port=self._port,
            log_level="warning", access_log=False,
        )
        self._servidor = _Servidor(config)
        self._thread = threading.Thread(target=self._servidor.run, daemon=True, name="tifa-web")
        self._thread.start()
        # Uvicorn arranca de forma asíncrona en ese hilo; se espera a que
        # `started` sea cierto (o a que el hilo muera por un error, p.ej. el
        # puerto ya en uso) para no devolver el control antes de tiempo.
        while not self._servidor.started and self._thread.is_alive():
            self._thread.join(timeout=0.05)
        if not self._thread.is_alive():
            self._servidor = None
            self._thread = None
            raise RuntimeError("El servidor web no pudo arrancar (¿puerto ocupado?)")
        self._log(f"Servidor web escuchando en {self.url}")

    def stop(self) -> None:
        """Pide la parada y espera a que muera el hilo. Idempotente."""
        self._stop_event.set()
        if self._servidor is None:
            return
        self._servidor.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._servidor = None
        self._thread = None
        self._log("Servidor web parado")

    def wait_forever(self) -> None:
        """Bloquea hasta Ctrl+C. Solo para `run_web.py`; la app de escritorio
        nunca debería llamar a esto -su hilo de UI se quedaría aquí atascado."""
        try:
            while not self._stop_event.wait(0.5):
                pass
        except KeyboardInterrupt:
            self._log("Ctrl+C recibido, parando...")
        finally:
            self.stop()
