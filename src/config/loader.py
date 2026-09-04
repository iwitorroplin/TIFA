


from pathlib import Path

import yaml


class ConfigLoader:

    """
    Clase para cargar archivos de configuración en formato YAML.
    """

    def __init__(self, config_path: Path):
        self.config_path = config_path

    def load(self) -> dict:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)