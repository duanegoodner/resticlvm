from dataclasses import dataclass
from pathlib import Path
import subprocess

from resticlvm.utils_run import optional_run, run_with_sudo


@dataclass
class ResticRepoNew:
    repo_path: Path
    password_file: Path
    dry_run: bool = False


class ResticRepo:
    def __init__(self, repo_path, password_file):
        self.repo_path = repo_path
        self.password_file = password_file

    @property
    def base_command(self) -> list[str]:
        return [
            "restic",
            "-r",
            str(self.repo_path),
            f"--password-file={str(self.password_file)}",
        ]

    def backup(self, source_path: str, exclude_paths: list[Path] = None):

        exclude_args = (
            [f"--exclude={str(path)}" for path in exclude_paths]
            if exclude_paths
            else []
        )

        run_with_sudo(
            cmd=self.base_command
            + ["backup", str(source_path), "--verbose"]
            + exclude_args,
            password="test123",
        )

    def list_snapshots(self):
        cmd = f"export RESTIC_PASSWORD_FILE={self.password_file}; restic -r {self.repo_path} snapshots"
        if self.dry_run:
            print(f"[DRY RUN] Would list snapshots with: {cmd}")
        else:
            print("Fetching snapshots from restic repo...\n")
            subprocess.run(args=cmd, shell=True, check=True)
