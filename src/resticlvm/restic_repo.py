"""
Defines classes and utilities for representing Restic repositories
and managing prune operations based on backup configurations.
"""

import importlib.resources as pkg_resources
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from resticlvm import scripts


@dataclass
class ResticPruneKeepParams:
    """Stores Restic prune retention parameters."""

    last: int
    daily: int
    weekly: int
    monthly: int
    yearly: int


@dataclass
class ResticRepo:
    """Represents a Restic repository and associated pruning settings."""

    repo_path: Path
    password_file: Path
    prune_keep_params: ResticPruneKeepParams

    def prune(self, dry_run: bool = False):
        """Prune snapshots in the Restic repository.

        Args:
            dry_run (bool, optional): If True, perform a dry-run without
                actually deleting any snapshots. Defaults to False.

        Raises:
            subprocess.CalledProcessError: If the Restic prune command fails.
            Exception: For unexpected errors during the prune operation.
        """
        script_path = pkg_resources.files(scripts) / "prune_repo.sh"

        cmd = [
            "bash",
            str(script_path),
            str(self.repo_path),
            str(self.password_file),
            str(self.prune_keep_params.last),
            str(self.prune_keep_params.daily),
            str(self.prune_keep_params.weekly),
            str(self.prune_keep_params.monthly),
            str(self.prune_keep_params.yearly),
        ]
        if dry_run:
            cmd.append("--dry-run")

        print(f"▶️ Pruning repo {self.repo_path} (dry-run={dry_run})")

        try:
            subprocess.run(
                cmd, check=True, stdout=sys.stdout, stderr=sys.stderr
            )
            print(f"✅ Prune completed for {self.repo_path}\n")
        except subprocess.CalledProcessError as e:
            print(f"❌ Prune failed for {self.repo_path}: {e}")
        except Exception as e:
            print(
                f"❌ Unexpected error during prune for {self.repo_path}: {e}"
            )


def confirm_unique_repos(config: dict) -> dict[tuple[str, str], ResticRepo]:
    """Ensure that all repositories in the config are unique.

    Args:
        config (dict): Parsed configuration dictionary.

    Returns:
        dict[tuple[str, str], ResticRepo]: Mapping of (category, job_name) to
        ResticRepo instances.

    Raises:
        ValueError: If duplicate repository paths are detected.
    """
    seen_repos = {}
    repo_paths_seen = set()

    for category in config.keys():
        for job_name, job_config in config[category].items():
            repo = job_config["restic_repo"]
            if repo in repo_paths_seen:
                raise ValueError(f"Duplicate repo detected: {repo}")
            repo_paths_seen.add(repo)

            seen_repos[(category, job_name)] = ResticRepo(
                repo_path=Path(repo),
                password_file=Path(job_config["restic_password_file"]),
                prune_keep_params=ResticPruneKeepParams(
                    last=int(job_config["prune_keep_last"]),
                    daily=int(job_config["prune_keep_daily"]),
                    weekly=int(job_config["prune_keep_weekly"]),
                    monthly=int(job_config["prune_keep_monthly"]),
                    yearly=int(job_config["prune_keep_yearly"]),
                ),
            )
    return seen_repos
