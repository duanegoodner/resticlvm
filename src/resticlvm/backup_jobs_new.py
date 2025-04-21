import os

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from pdb import run
from resticlvm.utils_chroot import (
    post_chroot_cleanup,
    prepare_for_chroot,
)
from resticlvm.utils_mount import remount_readonly, remount_rw
from resticlvm.logical_volume import LogicalVolume, LVMSnapshot
from resticlvm.utils_run import run_with_sudo


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


@dataclass
class ResticPathBackupJob:
    path_to_backup: Path
    repo_path: Path
    repo_password_file: Path
    exclude_paths: list[Path]
    remount_readonly: bool

    def __post_init__(self):
        if self.remount_readonly and not self.is_mount_point:
            raise ValueError(
                f"Path {self.path_to_backup} is not a mount point, cannot remount."
            )

    @property
    def is_mount_point(self) -> bool:
        return os.path.ismount(self.path_to_backup)

    @property
    def exclude_args(self) -> list[str]:
        return [f"--exclude={p}" for p in self.exclude_paths]

    @property
    def backup_cmd(self) -> list[str]:
        return (
            [
                "export",
                f"RESTIC_PASSWORD_FILE={self.repo_password_file};",
                "restic",
            ]
            + self.exclude_args
            + [
                "-r",
                self.repo_path,
                "backup",
                str(self.path_to_backup),
                "--verbose",
            ]
        )

    def run(self):
        if self.remount_readonly:
            with temporary_remount_readonly(path=self.path_to_backup):
                run_with_sudo(cmd=self.backup_cmd, password="test123")
        else:
            run_with_sudo(cmd=self.backup_cmd, password="test123")


@dataclass
class ResticLVMBackupJob:
    vg_name: str
    lv_name: str
    snapshot_mount_point: Path
    snapshot_size: int
    snapshot_size_unit: str
    repo_path: Path
    repo_password_file: Path
    paths_for_backup: list[Path]
    exclude_paths: list[Path]

    @classmethod
    def from_config(cls, config: dict) -> "ResticLVMBackupJob":
        return cls(
            vg_name=config["vg_name"],
            lv_name=config["lv_name"],
            snapshot_mount_point=Path(config["snapshot_mount_point"]),
            snapshot_size=int(config["snapshot_size"]),
            snapshot_size_unit=config["snapshot_size_unit"],
            repo_path=Path(config["repo_path"]),
            repo_password_file=Path(config["repo_password_file"]),
            paths_for_backup=[Path(p) for p in config["paths_for_backup"]],
            exclude_paths=[Path(p) for p in config["exclude_paths"]],
        )

    @property
    def logical_volume(self) -> LogicalVolume:
        return LogicalVolume(vg_name=self.vg_name, lv_name=self.lv_name)

    @property
    def exclude_args(self) -> list[str]:
        return [f"--exclude={p}" for p in self.exclude_paths]

    def backup_path_to_repo(self, path: Path) -> list[str]:
        run_with_sudo(
            cmd=[
                "export",
                f"RESTIC_PASSWORD_FILE={self.repo_password_file}",
                "restic",
                self.exclude_args,
                "-r",
                self.repo_path,
                "backup",
                str(path),
                "--verbose",
            ]
        )

    def run(self):
        # Create a snapshot of the logical volume
        snapshot = LVMSnapshot(
            origin=self.logical_volume,
            size=self.snapshot_size,
            size_unit=self.snapshot_size_unit,
            mount_point=self.snapshot_mount_point,
            dry_run=self.dry_run,
        )

        snapshot.prepare_for_backup()

        bind_targets = prepare_for_chroot(
            chroot_base=self.snapshot_mount_point,
            extra_sources=[self.repo_path],
        )

        run_with_sudo(
            cmd=["chroot", str(self.snapshot_mount_point)], password="test123"
        )

        for path in self.paths_for_backup:
            self.backup_path_to_repo(path=path)

        run_with_sudo(cmd=["exit"], password="test123")

        post_chroot_cleanup(bind_targets=bind_targets)

        snapshot.post_backup_cleanup()
