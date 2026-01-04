"""
Defines the BackupPlan class, which loads a backup configuration
and creates executable backup job instances based on it.
"""

from pathlib import Path

from resticlvm.orchestration.config_loader import load_config
from resticlvm.orchestration.data_classes import BackupJob, TokenConfigKeyPair
from resticlvm.orchestration.dispatch import RESOURCE_DISPATCH
from resticlvm.orchestration.restic_repo import ResticRepo, ResticPruneKeepParams


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

        Supports both new format (repositories array) and old format (single repo)
        for backward compatibility.

        Args:
            category (str): The backup category (e.g., 'standard_path', 'logical_volume_root').
            name (str): The name of the backup job.

        Returns:
            BackupJob: An initialized BackupJob object ready to run.

        Raises:
            ValueError: If the given category is not recognized or if duplicate
                repositories are found within the same job.
        """
        if category not in RESOURCE_DISPATCH:
            raise ValueError(f"Invalid backup category: {category}")

        dispatch = RESOURCE_DISPATCH[category]
        script_name = dispatch["script_name"]
        token_key_map = dispatch["token_key_map"]

        config = self.full_config[category][name]

        # Parse repositories - support both old and new formats
        repositories = []
        job_repo_paths = set()
        
        if "repositories" in config:
            # New format: multiple repositories per job
            for repo_config in config["repositories"]:
                repo_path_str = repo_config["repo_path"]
                
                # Check for duplicates within this job
                if repo_path_str in job_repo_paths:
                    raise ValueError(
                        f"Duplicate repo within job [{category}.{name}]: {repo_path_str}"
                    )
                job_repo_paths.add(repo_path_str)
                
                # Create ResticRepo object
                repositories.append(ResticRepo(
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
