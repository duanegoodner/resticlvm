import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from re import I

from resticlvm.utils import optional_run


class BootDir:
    def __init__(
        self, password_file: str, repo_path: str, dry_run: bool = False
    ):
        self.password_file = password_file
        self.repo_path = repo_path
        self.boot_partition = None
        self.dry_run = dry_run

    def run(self, cmd: str):
        print(f"[DRY RUN] {cmd}" if self.dry_run else f"Running: {cmd}")
        if not self.dry_run:
            subprocess.run(args=cmd, shell=True, check=True)

    def remount_readonly(self):
        if self.dry_run:
            self.boot_partition = "/dev/fakeboot"
            print("[DRY RUN] Pretending /boot is mounted.")
            return

        result = subprocess.run(
            args="mount | grep 'on /boot '",
            shell=True,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("/boot is not mounted. Skipping.")
            return

        self.boot_partition = result.stdout.split()[0]
        self.run(cmd=f"mount -o remount,ro {self.boot_partition}")

    def remount_rw(self):
        if self.boot_partition:
            self.run(cmd=f"mount -o remount,rw {self.boot_partition}")


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
        dry_run: bool = False,
    ):
        self.origin = origin
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        name = f"{origin.lv_name}_snap_{timestamp}"
        self.name = name
        self.size = size
        self.size_unit = size_unit
        self.mount_point = mount_point
        self.dry_run = dry_run
        self.create()

    @classmethod
    def of_logical_volume(
        cls,
        logical_volume: LogicalVolume,
        snap_size: str,
        mount_point: str,
        dry_run: bool,
    ):
        return cls(
            logical_volume=logical_volume,
            # snap_name=snap_name,
            snap_size=snap_size,
            mount_point=mount_point,
            dry_run=dry_run,
        )

    @property
    def device_path(self) -> Path:
        return Path(f"/dev/{self.origin.vg_name}/{self.name}")

    def create(self):
        cmd = [
            "lvcreate",
            "--size",
            f"{str(self.size)}{self.size_unit}",
            "--snapshot",
            "--name",
            self.name,
            self.origin.device_path,
        ]

        optional_run(cmd=cmd, dry_run=self.dry_run)

    def mount(self):
        self.mount_point.mkdir(parents=True, exist_ok=True)
        self.run(cmd=f"mount {self.snapshot_path()} {self.mount_point}")

    def cleanup(self):
        print("Cleaning up snapshot...")
        # for sub in ["dev", "proc", "sys"]:
        #     self.run(cmd=f"umount {self.mount_point}/{sub}")
        unmount_cmd = [
            "umount",
            self.mount_point,
        ]
        optional_run(cmd=unmount_cmd, dry_run=self.dry_run)

        remove_cmd = [
            "lvremove",
            "-y",
            str(self.device_path),
        ]
        optional_run(cmd=remove_cmd, dry_run=self.dry_run)

        self.mount_point.rmdir()
