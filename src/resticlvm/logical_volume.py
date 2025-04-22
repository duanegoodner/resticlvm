from pdb import run
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from re import I

from resticlvm.utils_run import optional_run, run_with_sudo


# class BootDir:
#     def __init__(
#         self, password_file: str, repo_path: str, dry_run: bool = False
#     ):
#         self.password_file = password_file
#         self.repo_path = repo_path
#         self.boot_partition = None
#         self.dry_run = dry_run

#     def run(self, cmd: str):
#         print(f"[DRY RUN] {cmd}" if self.dry_run else f"Running: {cmd}")
#         if not self.dry_run:
#             subprocess.run(args=cmd, shell=True, check=True)

#     def remount_readonly(self):
#         if self.dry_run:
#             self.boot_partition = "/dev/fakeboot"
#             print("[DRY RUN] Pretending /boot is mounted.")
#             return

#         result = subprocess.run(
#             args="mount | grep 'on /boot '",
#             shell=True,
#             capture_output=True,
#             text=True,
#         )
#         if result.returncode != 0:
#             print("/boot is not mounted. Skipping.")
#             return

#         self.boot_partition = result.stdout.split()[0]
#         self.run(cmd=f"mount -o remount,ro {self.boot_partition}")

#     def remount_rw(self):
#         if self.boot_partition:
#             self.run(cmd=f"mount -o remount,rw {self.boot_partition}")


class LogicalVolume:
    def __init__(self, vg_name: str, lv_name: str):
        self.vg_name = vg_name
        self.lv_name = lv_name

    @property
    def device_path(self) -> Path:
        return Path(f"/dev/{self.vg_name}/{self.lv_name}")


class LVMSnapshot:
    def __init__(
        self,
        origin: LogicalVolume,
        size: int,
        size_unit: str,
        mount_point: Path,
    ):
        self.origin = origin
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        name = f"{origin.lv_name}_snap_{timestamp}"
        self.name = name
        self.size = size
        self.size_unit = size_unit
        self.mount_point = mount_point
        self._create()

    def __enter__(self):
        self.prepare_for_backup()
        return self

    def __exit__(self):
        self.post_backup_cleanup()

    @property
    def device_path(self) -> Path:
        return Path(f"/dev/{self.origin.vg_name}/{self.name}")

    def _create(self):
        cmd = [
            "lvcreate",
            "--size",
            f"{str(self.size)}{self.size_unit}",
            "--snapshot",
            "--name",
            self.name,
            self.origin.device_path,
        ]

        run_with_sudo(cmd=cmd, password="test123")

    def create_mount_point(self):
        run_with_sudo(
            cmd=["mkdir", "-p", str(self.mount_point)], password="test123"
        )

    def delete_mount_point(self):
        run_with_sudo(cmd=["rmdir", str(self.mount_point)], password="test123")

    def mount(self):
        cmd = [
            "mount",
            str(self.device_path),
            str(self.mount_point),
        ]
        run_with_sudo(cmd=cmd, password="test123")

    def prepare_for_backup(self):
        self.create_mount_point()
        self.mount()

    def unmount(self):
        cmd = [
            "umount",
            str(self.mount_point),
        ]
        run_with_sudo(cmd=cmd, password="test123")

    def destroy(self):
        cmd = [
            "lvremove",
            "-y",
            str(self.device_path),
        ]
        run_with_sudo(cmd=cmd, password="test123")

    def post_backup_cleanup(self):
        self.unmount()
        # self.mount_point.rmdir()
        run_with_sudo(cmd=["rmdir", str(self.mount_point)])
        self.destroy()
