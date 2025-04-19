import subprocess
from pathlib import Path
from datetime import datetime


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

    def get_device_path(self) -> str:
        return f"/dev/{self.vg_name}/{self.lv_name}"



class LVMSnapshot:
    def __init__(
        self,
        logical_volume: LogicalVolume,
        snap_size: str,
        mount_point: str,
        dry_run: bool = False,
    ):
        self.of_logical_volume = logical_volume
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        snap_name = f"{logical_volume.vg_name}_{logical_volume.lv_name}_snap_{timestamp}"
        self.snap_name = snap_name
        self.snap_size = snap_size
        self.mount_point = Path(mount_point)
        self.dry_run = dry_run

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

    def run(self, cmd: str):
        print(f"[DRY RUN] {cmd}" if self.dry_run else f"Running: {cmd}")
        if not self.dry_run:
            subprocess.run(args=cmd, shell=True, check=True)

    def snapshot_path(self):
        return f"/dev/{self.lv.vg_name}/{self.snap_name}"

    def create(self):
        self.run(
            cmd=f"lvcreate --size {self.snap_size} --snapshot --name {self.snap_name} {self.lv.get_device_path()}"
        )

    def mount(self):
        self.mount_point.mkdir(parents=True, exist_ok=True)
        self.run(cmd=f"mount {self.snapshot_path()} {self.mount_point}")

    def bind_mount(self, source: str, target_rel: str):
        target = self.mount_point / target_rel.strip("/")
        target.mkdir(parents=True, exist_ok=True)
        self.run(cmd=f"mount --bind {source} {target}")

    def cleanup(self):
        print("Cleaning up snapshot...")
        for sub in ["dev", "proc", "sys"]:
            self.run(cmd=f"umount {self.mount_point}/{sub}")
        self.run(cmd=f"umount {self.mount_point}")
        self.run(cmd=f"lvremove -y {self.snapshot_path()}")
        self.mount_point.rmdir()
