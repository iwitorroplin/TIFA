"""
Punto de entrada del servidor web de TIFA (modo desarrollo):

python run_web.py

Proceso aparte de la app de escritorio (`run_app.py`) a propósito: se puede
reiniciar el servidor web sin cerrar TIFA y al revés. El día que se arranque
desde la interfaz, `web.server.TifaWebServer` se usa con `start()`/`stop()`
igual que aquí y este fichero sigue valiendo para desarrollo y pruebas.
"""

from web.log import make_file_log
from web.server import TifaWebServer


def main() -> None:
    servidor = TifaWebServer(log=make_file_log())
    servidor.start()
    servidor.wait_forever()


if __name__ == "__main__":
    main()
