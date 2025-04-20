from dataclasses import dataclass
from pathlib import Path
import subprocess

from resticlvm.utils_run import optional_run


@dataclass
class ResticRepoNew:
    repo_path: Path
    password_file: Path
    dry_run: bool = False


class ResticRepo:
    def __init__(self, repo_path, password_file, dry_run=False):
        self.repo_path = repo_path
        self.password_file = password_file
        self.dry_run = dry_run

    def backup(
        self, source_path: str, excludes: list[str] = None, chroot_path=None
    ):
        exclude_args = [f"--exclude={x}" for x in excludes] if excludes else []

        base_cmd = (
            [
                "export",
                f"RESTIC_PASSWORD_FILE={self.password_file};",
                "restic",
            ]
            + exclude_args
            + [
                "-r",
                self.repo_path,
                "backup",
                source_path,
                "--verbose",
            ]
        )

        if chroot_path:
            cmd = [
                "chroot",
                chroot_path,
                "/bin/bash",
                "-c",
            ] + base_cmd
        else:
            cmd = base_cmd

        optional_run(cmd=cmd, dry_run=self.dry_run)

    def list_snapshots(self):
        cmd = f"export RESTIC_PASSWORD_FILE={self.password_file}; restic -r {self.repo_path} snapshots"
        if self.dry_run:
            print(f"[DRY RUN] Would list snapshots with: {cmd}")
        else:
            print("Fetching snapshots from restic repo...\n")
            subprocess.run(args=cmd, shell=True, check=True)
