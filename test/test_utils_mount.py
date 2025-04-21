from pathlib import Path

import pytest

from resticlvm.utils_mount import (
    remount_readonly,
    remount_rw,
    temporary_remount_readonly,
)


@pytest.fixture
def boot_path():
    return Path("/boot")


def get_mount_options(path: Path) -> list[str]:
    with open("/proc/mounts") as f:
        for line in f:
            parts = line.split()
            if parts[1] == str(path):
                return parts[3].split(",")
    raise RuntimeError(f"Mount point {path} not found in /proc/mounts")


def is_rw(path: Path) -> bool:
    opts = get_mount_options(path)
    return "rw" in opts and "ro" not in opts


def is_ro(path: Path) -> bool:
    opts = get_mount_options(path)
    return "ro" in opts and "rw" not in opts


def test_boot_remount(boot_path):
    # boot_path = Path("/boot")
    remount_readonly(path=boot_path)
    assert is_ro(path=boot_path), "Expected /boot to be read-only"
    remount_rw(path=boot_path)
    assert is_rw(path=boot_path), "Expected /boot to be read-write"


def test_temporary_remount_readonly_success(boot_path):
    # Ensure clean state
    assert is_rw(boot_path), "/boot should start as read-write"

    with temporary_remount_readonly(boot_path):
        assert is_ro(boot_path), "/boot should be read-only inside context"

    # After context, back to read-write
    assert is_rw(boot_path), "/boot should be back to read-write after context"


def test_temporary_remount_readonly_exception_safety(boot_path):
    assert is_rw(boot_path)

    with pytest.raises(RuntimeError, match="boom"):
        with temporary_remount_readonly(boot_path):
            assert is_ro(boot_path)
            raise RuntimeError("boom")

    assert is_rw(boot_path), "/boot should be restored even after exception"
