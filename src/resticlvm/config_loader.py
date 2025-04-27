import tomllib
from pathlib import Path


def load_config(path: str | Path) -> dict:
    import_path = Path(path)
    with import_path.open(mode="rb") as f:
        config_dict = tomllib.load(f)
    return config_dict
