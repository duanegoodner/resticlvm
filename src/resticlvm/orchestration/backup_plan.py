"""
Defines the BackupPlan class, which loads a backup configuration
and creates executable backup job instances based on it.
"""

from pathlib import Path

from resticlvm.orchestration.config_loader import load_config
from resticlvm.orchestration.data_classes import BackupJob, TokenConfigKeyPair
from resticlvm.orchestration.dispatch import RESOURCE_DISPATCH
from resticlvm.orchestration.restic_repo import (
    ResticRepo,
    ResticPruneKeepParams,
    CopyDestination,
)


class BackupPlan:
    """Represents a collection of backup jobs based on a configuration file."""

    def __init__(self, config_path: Path, dry_run: bool = False):
        """Initialize a BackupPlan.

        Args:
            config_path (Path): Path to the configuration TOML file.
            dry_run (bool, optional): If True, simulate backup actions without
                executing them. Defaults to False.
        """
        self.config_path = config_path
        self.full_config = load_config(config_path)
        self.dry_run = dry_run

    def create_backup_job(self, category: str, name: str) -> BackupJob:
        """Create a BackupJob instance from a specific category and job name.

        Args:
            category (str): The backup category (e.g., 'standard_path', 'logical_volume_root').
            name (str): The name of the backup job.

        Returns:
            BackupJob: An initialized BackupJob object ready to run.

        Raises:
            ValueError: If the given category is not recognized.
        """
        if category not in RESOURCE_DISPATCH:
            raise ValueError(f"Invalid backup category: {category}")

        dispatch = RESOURCE_DISPATCH[category]
        script_name = dispatch["script_name"]
        token_key_map = dispatch["token_key_map"]

        config = self.full_config[category][name]

        # Build list of ResticRepo instances
        repositories = []
        if "repositories" in config:
            # New format: array of repositories
            for repo_config in config["repositories"]:
                # Parse copy_to destinations if present
                copy_destinations = []
                if "copy_to" in config:
                    for copy_config in config["copy_to"]:
                        copy_destinations.append(CopyDestination(
                            repo_path=copy_config["repo"],
                            password_file=Path(copy_config["password_file"]),
                            prune_keep_params=ResticPruneKeepParams(
                                last=int(copy_config["prune_keep_last"]),
                                daily=int(copy_config["prune_keep_daily"]),
                                weekly=int(copy_config["prune_keep_weekly"]),
                                monthly=int(copy_config["prune_keep_monthly"]),
                                yearly=int(copy_config["prune_keep_yearly"]),
                            ),
                        ))
                
                repositories.append(ResticRepo(
                    repo_path=Path(repo_config["repo_path"]),
                    password_file=Path(repo_config["password_file"]),
                    prune_keep_params=ResticPruneKeepParams(
                        last=int(repo_config["prune_keep_last"]),
                        daily=int(repo_config["prune_keep_daily"]),
                        weekly=int(repo_config["prune_keep_weekly"]),
                        monthly=int(repo_config["prune_keep_monthly"]),
                        yearly=int(repo_config["prune_keep_yearly"]),
                    ),
                    copy_destinations=copy_destinations,
                ))
        else:
            # Old format: single repo (backward compatibility)
            repositories.append(ResticRepo(
                repo_path=Path(config["restic_repo"]),
                password_file=Path(config["restic_password_file"]),
                prune_keep_params=ResticPruneKeepParams(
                    last=int(config["prune_keep_last"]),
                    daily=int(config["prune_keep_daily"]),
                    weekly=int(config["prune_keep_weekly"]),
                    monthly=int(config["prune_keep_monthly"]),
                    yearly=int(config["prune_keep_yearly"]),
                ),
            ))

        return BackupJob(
            script_name=script_name,
            script_token_config_key_pairs=TokenConfigKeyPair.from_token_key_map(
                token_key_map
            ),
            config=config,
            name=name,
            category=category,
            repositories=repositories,
            dry_run=self.dry_run,
        )

    @property
    def backup_jobs(self) -> list[BackupJob]:
        """List all backup jobs defined in the configuration.

        Returns:
            list[BackupJob]: List of BackupJob instances.
        """
        jobs = []
        for category, jobs_dict in self.full_config.items():
            for job_name in jobs_dict.keys():
                jobs.append(self.create_backup_job(category, job_name))
        return jobs
