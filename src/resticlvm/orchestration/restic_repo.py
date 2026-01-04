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


def confirm_unique_repos(config: dict) -> dict[tuple[str, str], list[ResticRepo]]:
    """Ensure that repositories within each job are unique.

    Parses the configuration and builds ResticRepo objects. Supports both
    old format (single repo per job) and new format (multiple repos per job).
    
    Args:
        config (dict): Parsed configuration dictionary.

    Returns:
        dict[tuple[str, str], list[ResticRepo]]: Mapping of (category, job_name)
        to lists of ResticRepo instances.

    Raises:
        ValueError: If duplicate repository paths are detected within the same job.
    """
    all_repos = {}

    for category in config.keys():
        for job_name, job_config in config[category].items():
            job_repos = []
            job_repo_paths = set()
            
            # Check if using new format (repositories array) or old format (single repo)
            if "repositories" in job_config:
                # New format: multiple repositories per job
                for repo_config in job_config["repositories"]:
                    repo_path_str = repo_config["repo_path"]
                    
                    # Check for duplicates within this job
                    if repo_path_str in job_repo_paths:
                        raise ValueError(
                            f"Duplicate repo within job [{category}.{job_name}]: {repo_path_str}"
                        )
                    job_repo_paths.add(repo_path_str)
                    
                    # Create ResticRepo object
                    job_repos.append(ResticRepo(
                        repo_path=Path(repo_path_str),
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
                # Old format: single repository per job (backward compatibility)
                repo_path_str = job_config["restic_repo"]
                job_repos.append(ResticRepo(
                    repo_path=Path(repo_path_str),
                    password_file=Path(job_config["restic_password_file"]),
                    prune_keep_params=ResticPruneKeepParams(
                        last=int(job_config["prune_keep_last"]),
                        daily=int(job_config["prune_keep_daily"]),
                        weekly=int(job_config["prune_keep_weekly"]),
                        monthly=int(job_config["prune_keep_monthly"]),
                        yearly=int(job_config["prune_keep_yearly"]),
                    ),
                ))
            
            all_repos[(category, job_name)] = job_repos
    
    return all_repos
