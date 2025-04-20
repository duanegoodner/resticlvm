from dataclasses import dataclass
from pathlib import Path
from resticlvm.chroot_utils import optional_run_with_chroot, prepare_for_chroot
from resticlvm.mount_utils import remount_readonly, remount_rw
from resticlvm.local_classes import LogicalVolume, LVMSnapshot
from resticlvm.utils_run import optional_run


@dataclass
class ResticPathBackupJob:
    path_to_backup: Path
    repo_path: Path
    repo_password_file: Path
    exclude_paths: list[Path]
    remount_readonly: bool
    dry_run: bool

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
            remount_readonly(path=self.path_to_backup, dry_run=self.dry_run)

        optional_run(
            cmd=self.backup_cmd,
            dry_run=self.dry_run,
        )

        if self.remount_readonly:
            remount_rw(path=self.path_to_backup, dry_run=self.dry_run)

    # def send_to_restic_repo(self):


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
    dry_run: bool

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

    def run(self):
        # Create a snapshot of the logical volume
        snapshot = LVMSnapshot(
            origin=self.logical_volume,
            size=self.snapshot_size,
            size_unit=self.snapshot_size_unit,
            mount_point=self.snapshot_mount_point,
            dry_run=self.dry_run,
        )

        # Mount the snapshot
        optional_run(
            cmd=[
                "mount",
                str(snapshot.device_path),
                str(snapshot.mount_point),
            ],
            dry_run=False,
        )

        prepare_for_chroot(
            chroot_base=self.snapshot_mount_point, dry_run=self.dry_run
        )

        optional_run_with_chroot()

        # Run the backup job
        backup_job = ResticPathBackupJob(
            path_to_backup=snapshot.mount_point,
            repo_path=self.repo_path,
            repo_password_file=self.repo_password_file,
            exclude_paths=self.exclude_paths,
            remount_readonly=True,
            dry_run=False,
        )
        backup_job.run()

        # Unmount the snapshot
        optional_run(
            cmd=[
                "umount",
                str(snapshot.mount_point),
            ],
            dry_run=False,
        )
