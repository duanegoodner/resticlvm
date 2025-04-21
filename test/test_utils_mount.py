from resticlvm.utils_mount import remount_readonly, remount_rw
from pathlib import Path


def get_mount_options(path: Path) -> list[str]:
    with open("/proc/mounts") as f:
        for line in f:
            parts = line.split()
            if parts[1] == str(path):
                return parts[3].split(",")
    raise RuntimeError(f"Mount point {path} not found in /proc/mounts")


def test_boot_remount():
    boot_path = Path("/boot")
    remount_readonly(path=boot_path)
    assert "ro" in get_mount_options(
        boot_path
    ), "Expected /boot to be remounted as read-only"
    remount_rw(path=boot_path)
    assert "rw" in get_mount_options(
        boot_path
    ), "Expected /boot to be remounted as read-write"
