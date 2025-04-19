import subprocess
from typing import List


class ResticRepo:
    def __init__(self, repo_path, password_file, dry_run=False):
        self.repo_path = repo_path
        self.password_file = password_file
        self.dry_run = dry_run

    def run(self, cmd):
        print(f"[DRY RUN] {cmd}" if self.dry_run else f"Running: {cmd}")
        if not self.dry_run:
            subprocess.run(args=cmd, shell=True, check=True)

    def backup(
        self, source_path: str, excludes: List[str] = None, chroot_path=None
    ):
        exclude_args = (
            " ".join([f"--exclude={x}" for x in excludes]) if excludes else ""
        )
        base_cmd = f"export RESTIC_PASSWORD_FILE={self.password_file}; restic {exclude_args} -r {self.repo_path} backup {source_path} --verbose"

        if chroot_path:
            cmd = f'chroot {chroot_path} /bin/bash -c "{base_cmd}"'
        else:
            cmd = base_cmd

        self.run(cmd=cmd)

    def list_snapshots(self):
        cmd = f"export RESTIC_PASSWORD_FILE={self.password_file}; restic -r {self.repo_path} snapshots"
        if self.dry_run:
            print(f"[DRY RUN] Would list snapshots with: {cmd}")
        else:
            print("Fetching snapshots from restic repo...\n")
            subprocess.run(args=cmd, shell=True, check=True)
