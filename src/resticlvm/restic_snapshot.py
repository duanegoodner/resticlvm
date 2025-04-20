import os
from dataclasses import dataclass
from pathlib import Path

from resticlvm.local_classes import BootDir, LVMSnapshot
from resticlvm.restic_classes import ResticRepo
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

    def send_to_restic_repo(self):


    
    def run(self):
        if self.remount_readonly:
            remount_readonly(path=self.path_to_backup, dry_run=self.dry_run)

        exclude_args = [f"--exclude={p}" for p in self.exclude_paths]

        cmd = (
            [
                "export",
                f"RESTIC_PASSWORD_FILE={self.repo_password_file};",
                "restic",
            ]
            + exclude_args
            + [
                "-r",
                self.repo_path,
                "backup",
                str(self.path_to_backup),
                "--verbose",
            ]
        )

        optional_run(cmd=cmd, dry_run=self.dry_run)





@dataclass
class ResticLVMSnapshot:
    lvm_snapshot: LVMSnapshot
    restic_repo: ResticRepo
    paths_for_backup: list[str]
    exclude_paths: list[str]

    def send(self):
        # Ensure the snapshot is mounted and ready
        mount_point = self.lvm_snapshot.mount_point

        # exclude_args = [f"--exclude={p}" for p in self.exclude_paths]

        # Backup each path relative to snapshot mount point
        for path in self.paths_for_backup:
            backup_path = path  # Within chroot, it's absolute
            print(f"Backing up {backup_path} from snapshot...")

            self.restic_repo.backup(
                source_path=backup_path,
                excludes=self.exclude_paths,
                chroot_path=str(mount_point),
            )


@dataclass
class ResticBootSnapshot:
    boot_dir: BootDir
    restic_repo: ResticRepo

    def send(self):
        try:
            self.boot_dir.remount_readonly()
            cmd = f"restic -r {self.restic_repo.repo_path} "
            f"--password-file={self.restic_repo.password_file} backup /boot --verbose"
            self.boot_dir.run(cmd=cmd)
        finally:
            self.boot_dir.remount_rw()
