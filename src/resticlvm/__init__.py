"""ResticLVM — Restic + LVM backup orchestration.

The package version is single-sourced in ``pyproject.toml`` and exposed here at
runtime via installed package metadata.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("resticlvm")
except PackageNotFoundError:  # running from a source tree with no installed metadata
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
