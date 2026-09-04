# NOTA: pila de config provisional, pendiente de consolidar con files.py
# (ver structure_refactor.md, Fase 2). Nada la importa todavía.

from .loader import ConfigLoader
from .writer import ConfigWriter
from .paths import DEFAULT_CONFIG_DIR, APP_CONFIG_DIR


class ConfigManager:

    def __init__(self):
        self.default_path = DEFAULT_CONFIG_DIR
        self.user_path = APP_CONFIG_DIR

        self._cache = {}

    def load(self, name: str) -> dict:
        if name in self._cache:
            return self._cache[name]

        default_file = self.default_path / f"{name}.yaml"
        user_file = self.user_path / f"{name}.yaml"

        data = ConfigLoader(default_file).load()

        # Aquí posteriormente podemos hacer merge
        # con la configuración del usuario.

        if user_file.exists():
            user_data = ConfigLoader(user_file).load()
            data.update(user_data)

        self._cache[name] = data

        return data

    def save(self, name: str, data: dict) -> None:
        path = self.user_path / f"{name}.yaml"

        ConfigWriter().save(path, data)

        self._cache[name] = data