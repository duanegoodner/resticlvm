import os


from dataclasses import dataclass
from pathlib import Path
from pdb import run
from resticlvm.utils_chroot import (
    post_chroot_cleanup,
    prepare_for_chroot,
)
from resticlvm.utils_mount import temporary_remount_readonly
from resticlvm.logical_volume import LogicalVolume, LVMSnapshot
from resticlvm.restic_classes import ResticRepo
from resticlvm.utils_run import run_with_sudo


@dataclass
class ResticPathBackupJob:
    source: Path
    restic_repo: ResticRepo
    exclude_paths: list[Path]
    remount_readonly: bool

    @classmethod
    def from_config(cls, config: dict) -> "ResticPathBackupJob":
        return cls(
            source=Path(config["source"]),
            restic_repo=ResticRepo(
                repo_path=Path(config["repo_path"]),
                password_file=Path(config["repo_password_file"]),
            ),
            exclude_paths=[Path(p) for p in config["exclude_paths"]],
            remount_readonly=config["remount_readonly"],
        )

    def __post_init__(self):
        if self.remount_readonly and not self.is_for_mount_point:
            raise ValueError(
                f"Path {self.source} is not a mount point, cannot remount."
            )

    @property
    def is_for_mount_point(self) -> bool:
        return os.path.ismount(self.source)

    @property
    def exclude_args(self) -> list[str]:
        return [f"--exclude={p}" for p in self.exclude_paths]

    def run(self):
        if self.remount_readonly:
            with temporary_remount_readonly(path=self.source):
                self.restic_repo.backup(
                    source_path=self.source, exclude_paths=self.exclude_paths
                )
                # run_with_sudo(cmd=self.backup_cmd, password="test123")
        else:
            self.restic_repo.backup(
                source_path=self.source, exclude_paths=self.exclude_paths
            )
            # run_with_sudo(cmd=self.backup_cmd, password="test123")


@dataclass
class ResticLVMBackupJob:
    source_vg_name: str
    source_lv_name: str
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
            source_vg_name=config["source_vg_name"],
            source_lv_name=config["source_lv_name"],
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
        return LogicalVolume(
            vg_name=self.source_vg_name, lv_name=self.source_lv_name
        )

    @property
    def exclude_args(self) -> list[str]:
        return [f"--exclude={p}" for p in self.exclude_paths]

    @property
    def restic_path_backup_jobs(self) -> list[ResticPathBackupJob]:
        return [
            ResticPathBackupJob(
                source=path,
                repo_path=self.repo_path,
                repo_password_file=self.repo_password_file,
                exclude_paths=self.exclude_paths,
                remount_readonly=False,
            )
            for path in self.paths_for_backup
        ]

    def run(self):
        # Create a snapshot of the logical volume
        snapshot = LVMSnapshot(
            origin=self.logical_volume,
            size=self.snapshot_size,
            size_unit=self.snapshot_size_unit,
            mount_point=self.snapshot_mount_point,
        )

        snapshot.prepare_for_backup()

        bind_targets = prepare_for_chroot(
            chroot_base=self.snapshot_mount_point,
            extra_sources=[self.repo_path],
        )

        run_with_sudo(
            cmd=["chroot", str(self.snapshot_mount_point)], password="test123"
        )

        for path_backup_job in self.restic_path_backup_jobs:
            path_backup_job.run()

        run_with_sudo(cmd=["exit"], password="test123")

        post_chroot_cleanup(bind_targets=bind_targets)

        snapshot.post_backup_cleanup()
