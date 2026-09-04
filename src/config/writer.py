from pathlib import Path
import yaml


class ConfigWriter:

    def save(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as file:
            yaml.safe_dump(
                data,
                file,
                allow_unicode=True,
                sort_keys=False
            )