"""
Provides utilities for loading configuration files in TOML format
using the built-in tomllib module (Python 3.11+).
"""

import tomllib
from pathlib import Path


def load_config(path: str | Path) -> dict:
    """Load a TOML configuration file into a Python dictionary.

    Args:
        path (str | Path): Path to the configuration file.

    Returns:
        dict: Parsed configuration as a dictionary.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        tomllib.TOMLDecodeError: If the file contains invalid TOML syntax.
    """
    import_path = Path(path)
    with import_path.open(mode="rb") as f:
        config_dict = tomllib.load(f)
    return config_dict
