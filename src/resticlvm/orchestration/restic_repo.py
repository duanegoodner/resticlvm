"""
Defines classes and utilities for representing Restic repositories
and managing prune operations based on backup configurations.
"""

import importlib.resources as pkg_resources
import os
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
class CopyDestination:
    """Represents a destination repository for restic copy operations."""

    repo_path: str
    password_file: Path
    prune_keep_params: ResticPruneKeepParams


@dataclass
class ResticRepo:
    """Represents a Restic repository and associated pruning settings."""

    repo_path: Path
    password_file: Path
    prune_keep_params: ResticPruneKeepParams
    copy_destinations: list['CopyDestination'] = None

    def __post_init__(self):
        """Initialize copy_destinations as empty list if None."""
        if self.copy_destinations is None:
            self.copy_destinations = []

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

        # Prepare environment with SSH agent socket for SFTP repositories
        env = os.environ.copy()
        env['SSH_AUTH_SOCK'] = '/root/.ssh/ssh-agent.sock'

        try:
            subprocess.run(
                cmd, check=True, stdout=sys.stdout, stderr=sys.stderr, env=env
            )
            print(f"✅ Prune completed for {self.repo_path}\n")
        except subprocess.CalledProcessError as e:
            print(f"❌ Prune failed for {self.repo_path}: {e}")
        except Exception as e:
            print(
                f"❌ Unexpected error during prune for {self.repo_path}: {e}"
            )


def confirm_unique_repos(config: dict) -> dict[tuple[str, str], list[ResticRepo]]:
    """Ensure that repositories within each job are unique.

    Args:
        config (dict): Parsed configuration dictionary.

    Returns:
        dict[tuple[str, str], list[ResticRepo]]: Mapping of (category, job_name)
        to lists of ResticRepo instances.

    Raises:
        ValueError: If duplicate repository paths are detected within the same job.

    Note:
        The same repository can appear in different jobs, but not within the same job.
    """
    seen_repos = {}

    for category in config.keys():
        for job_name, job_config in config[category].items():
            repos_for_job = []
            repo_paths_in_job = set()

            # Handle both old (single repo) and new (repo array) formats
            if "repositories" in job_config:
                # New format: array of repositories
                for repo_config in job_config["repositories"]:
                    repo_path = repo_config["repo_path"]
                    if repo_path in repo_paths_in_job:
                        raise ValueError(
                            f"Duplicate repo '{repo_path}' in job [{category}.{job_name}]"
                        )
                    repo_paths_in_job.add(repo_path)

                    repos_for_job.append(ResticRepo(
                        repo_path=Path(repo_path),
                        password_file=Path(repo_config["password_file"]),
                        prune_keep_params=ResticPruneKeepParams(
                            last=int(repo_config["prune_keep_last"]),
                            daily=int(repo_config["prune_keep_daily"]),
                            weekly=int(repo_config["prune_keep_weekly"]),
                            monthly=int(repo_config["prune_keep_monthly"]),
                            yearly=int(repo_config["prune_keep_yearly"]),
                        ),
                    ))
            else:
                # Old format: single repo (backward compatibility)
                repo_path = job_config["restic_repo"]
                repos_for_job.append(ResticRepo(
                    repo_path=Path(repo_path),
                    password_file=Path(job_config["restic_password_file"]),
                    prune_keep_params=ResticPruneKeepParams(
                        last=int(job_config["prune_keep_last"]),
                        daily=int(job_config["prune_keep_daily"]),
                        weekly=int(job_config["prune_keep_weekly"]),
                        monthly=int(job_config["prune_keep_monthly"]),
                        yearly=int(job_config["prune_keep_yearly"]),
                    ),
                ))

            seen_repos[(category, job_name)] = repos_for_job

    return seen_repos
