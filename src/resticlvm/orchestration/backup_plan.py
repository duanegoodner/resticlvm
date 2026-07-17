"""
Defines the BackupPlan class, which loads a backup configuration
and creates executable backup job instances based on it.
"""

from pathlib import Path

from resticlvm.orchestration.backup_config import (
    BackupConfigFactory,
    RepoConfig,
    SnapshotSettings,
    VolumeConfig,
    VolumeType,
)
from resticlvm.orchestration.config_loader import load_config
from resticlvm.orchestration.config_validator import warn_on_validation_issues
from resticlvm.orchestration.data_classes import BackupJob, TokenConfigKeyPair
from resticlvm.orchestration.dispatch import RESOURCE_DISPATCH
from resticlvm.orchestration.restic_repo import (
    CopyDestination,
    ResticRepo,
)


def _to_restic_repo(repo_cfg: RepoConfig) -> ResticRepo:
    return ResticRepo(
        repo_path=Path(repo_cfg.repo_path),
        password_file=repo_cfg.password_file,
        prune_keep_params=repo_cfg.prune_keep_params,
        copy_destinations=[
            CopyDestination(
                repo_path=d.repo_path,
                password_file=d.password_file,
                prune_keep_params=d.prune_keep_params,
            )
            for d in repo_cfg.copy_destinations
        ],
    )


def _job_config_dict(vol_cfg: VolumeConfig) -> dict:
    """Build the dict that BackupJob uses for shell script arg building."""
    d = {
        "backup_source_path": vol_cfg.backup_source_path,
        "exclude_paths": vol_cfg.exclude_paths,
    }
    if vol_cfg.volume_type in (VolumeType.LV_ROOT, VolumeType.LV_NONROOT):
        d["vg_name"] = vol_cfg.vg_name
        d["lv_name"] = vol_cfg.lv_name
        d["snapshot_size"] = vol_cfg.snapshot_size
    return d


class BackupPlan:
    """Represents a collection of backup jobs based on a configuration file."""

    def __init__(self, config_path: Path, dry_run: bool = False):
        self.config_path = config_path
        self.dry_run = dry_run
        raw = load_config(config_path)
        self._config = BackupConfigFactory(raw).build()
        warn_on_validation_issues(self._config)

    def _build_backup_job(
        self, name: str, vol_cfg: VolumeConfig
    ) -> BackupJob:
        dispatch = RESOURCE_DISPATCH[vol_cfg.volume_type]
        return BackupJob(
            script_name=dispatch["script_name"],
            script_token_config_key_pairs=TokenConfigKeyPair.from_token_key_map(
                dispatch["token_key_map"]
            ),
            config=_job_config_dict(vol_cfg),
            name=name,
            category=vol_cfg.volume_type.value,
            repositories=[_to_restic_repo(r) for r in vol_cfg.repositories],
            dry_run=self.dry_run,
        )

    @property
    def backup_jobs(self) -> list[BackupJob]:
        return [
            self._build_backup_job(name, cfg)
            for name, cfg in self._config.volumes.items()
        ]

    @property
    def snapshot_settings(self) -> SnapshotSettings:
        return self._config.snapshot_settings
