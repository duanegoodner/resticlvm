from pathlib import Path

from resticlvm.config_loader import load_config
from resticlvm.data_classes import BackupJob, TokenConfigKeyPair
from resticlvm.dispatch import RESOURCE_DISPATCH


class BackupPlan:
    def __init__(self, config_path: Path, dry_run: bool = False):
        self.config_path = config_path
        self.full_config = load_config(config_path)
        self.dry_run = dry_run

    def create_backup_job(self, category: str, name: str) -> BackupJob:
        if category not in RESOURCE_DISPATCH:
            raise ValueError(f"Invalid backup category: {category}")

        dispatch = RESOURCE_DISPATCH[category]
        script_name = dispatch["script_name"]
        token_key_map = dispatch["token_key_map"]

        config = self.full_config[category][name]

        return BackupJob(
            script_name=script_name,
            script_token_config_key_pairs=TokenConfigKeyPair.from_token_key_map(
                token_key_map
            ),
            config=config,
            name=name,
            category=category,
            dry_run=self.dry_run,
        )

    @property
    def backup_jobs(self) -> list[BackupJob]:
        jobs = []
        for category, jobs_dict in self.full_config.items():
            for job_name in jobs_dict.keys():
                jobs.append(self.create_backup_job(category, job_name))
        return jobs
