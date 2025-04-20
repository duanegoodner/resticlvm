import os
from pathlib import Path

from resticlvm.utils_run import optional_run


def remount_readonly(path: Path, dry_run: bool):
    if not path.exists():
        raise FileNotFoundError(f"Path {str(path)} does not exist.")
    if not os.path.ismount(path):
        raise ValueError(f"Path {str(path)} is not a mount point.")
    optional_run(
        cmd=[
            "mount",
            "-o",
            "remount,ro",
            str(path),
        ],
        dry_run=dry_run,
    )


def remount_rw(path: Path, dry_run: bool):
    if not path.exists():
        raise FileNotFoundError(f"Path {str(path)} does not exist.")
    if not os.path.ismount(path):
        raise ValueError(f"Path {str(path)} is not a mount point.")
    optional_run(
        cmd=[
            "mount",
            "-o",
            "remount,rw",
            str(path),
        ],
        dry_run=dry_run,
    )
