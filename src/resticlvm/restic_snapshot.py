from dataclasses import dataclass
from typing import List

from resticlvm.local_classes import BootDir, LVMSnapshot
from resticlvm.restic_classes import ResticRepo


@dataclass
class ResticLVMSnapshot:
    lvm_snapshot: LVMSnapshot
    restic_repo: ResticRepo
    paths_for_backup: List[str]
    exclude_paths: List[str]

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
