import os
from contextlib import contextmanager
from pathlib import Path

from resticlvm.utils_run import run_with_sudo


def remount_readonly(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Path {str(path)} does not exist.")
    if not os.path.ismount(path):
        raise ValueError(f"Path {str(path)} is not a mount point.")

    run_with_sudo(
        cmd=[
            "mount",
            "-o",
            "remount,ro",
            str(path),
        ],
        password="test123",
    )


def remount_rw(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Path {str(path)} does not exist.")
    if not os.path.ismount(path):
        raise ValueError(f"Path {str(path)} is not a mount point.")
    run_with_sudo(
        cmd=[
            "mount",
            "-o",
            "remount,rw",
            str(path),
        ],
        password="test123",
    )


@contextmanager
def temporary_remount_readonly(path: Path):
    """
    Context manager to temporarily remount a path as read-only.
    """
    try:
        remount_readonly(path=path)
        yield
    finally:
        remount_rw(path=path)
