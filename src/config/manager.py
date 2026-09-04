from pathlib import Path

from .loader import ConfigLoader
from .writer import ConfigWriter
from .paths import APP_ROOT


class ConfigManager:

    def __init__(self):
        self.root = Path(__file__).resolve().parents[2] / "config"

        self.default_path = self.root / "default"
        self.user_path = self.root / "user"

        self.loader = ConfigLoader()
        self.writer = ConfigWriter()

        self._cache = {}

    def load(self, name: str) -> dict:
        if name in self._cache:
            return self._cache[name]

        default_file = self.default_path / f"{name}.yaml"
        user_file = self.user_path / f"{name}.yaml"

        data = self.loader.load(default_file)

        # Aquí posteriormente podemos hacer merge
        # con la configuración del usuario.

        if user_file.exists():
            user_data = self.loader.load(user_file)
            data.update(user_data)

        self._cache[name] = data

        return data

    def save(self, name: str, data: dict) -> None:
        path = self.user_path / f"{name}.yaml"

        self.writer.save(path, data)

        self._cache[name] = data