from dataclasses import dataclass
from pathlib import Path
import json
import subprocess

from resticlvm.utils_run import run_with_sudo


class ResticRepo:
    def __init__(self, repo_path: Path, password_file: Path):
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

    @property
    def snapshots_as_json(self) -> list[dict] | None:
        subproces_output = run_with_sudo(
            cmd=self.base_command + ["snapshots", "--json"], password="test123"
        )
        return json.loads(subproces_output.stdout)

    @property
    def num_snapshots(self) -> int:
        return len(self.snapshots_as_json) if self.snapshots_as_json else 0

    @property
    def latest_snapshot(self) -> str | None:
        if self.snapshots_as_json:
            return self.snapshots_as_json[-1]["short_id"]

    def forget_and_prune_snapshot(
        self, snapshot_id: str, dry_run: bool = False
    ):
        cmd = self.base_command + ["forget", snapshot_id, "--prune"]
        if dry_run:
            cmd.append("--dry-run")

        run_with_sudo(cmd=cmd, password="test123")

        print(f"Forgot snapshot {snapshot_id} (dry_run={dry_run})")

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

    # def list_snapshots(self):
    #     cmd = f"export RESTIC_PASSWORD_FILE={self.password_file}; restic -r {self.repo_path} snapshots"
    #     if self.dry_run:
    #         print(f"[DRY RUN] Would list snapshots with: {cmd}")
    #     else:
    #         print("Fetching snapshots from restic repo...\n")
    #         subprocess.run(args=cmd, shell=True, check=True)
