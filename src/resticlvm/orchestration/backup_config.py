"""Typed representation of a ResticLVM backup configuration file."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from resticlvm.orchestration.restic_repo import ResticPruneKeepParams


def _parse_prune_policy(raw: dict) -> ResticPruneKeepParams:
    return ResticPruneKeepParams(
        last=int(raw["keep_last"]),
        daily=int(raw["keep_daily"]),
        weekly=int(raw["keep_weekly"]),
        monthly=int(raw["keep_monthly"]),
        yearly=int(raw["keep_yearly"]),
    )


class VolumeType(Enum):
    STANDARD_PATH = "standard_path"
    LV_ROOT = "lv_root"
    LV_NONROOT = "lv_nonroot"


@dataclass
class CopyDestConfig:
    """A copy-to destination for a repository."""

    repo_path: str
    password_file: Path
    prune_keep_params: ResticPruneKeepParams


@dataclass
class RepoConfig:
    """A single backup repository."""

    repo_path: str
    password_file: Path
    prune_keep_params: ResticPruneKeepParams
    copy_destinations: list[CopyDestConfig] = field(default_factory=list)


@dataclass
class VolumeConfig:
    """Config for a backup volume."""

    volume_type: VolumeType
    backup_source_path: str
    exclude_paths: list[str]
    repositories: list[RepoConfig]
    vg_name: str | None = None
    lv_name: str | None = None
    snapshot_size: str | None = None


@dataclass
class SnapshotSettings:
    """Top-level snapshot coordination settings."""

    min_vg_free_after_snapshots: str = "1G"
    snapshot_cow_warn_percent: int = 70


@dataclass
class BackupConfig:
    """Typed, fully-resolved backup configuration."""

    prune_policies: dict[str, ResticPruneKeepParams]
    volumes: dict[str, VolumeConfig]
    snapshot_settings: SnapshotSettings = field(default_factory=SnapshotSettings)


class BackupConfigFactory:
    """Builds a BackupConfig from a raw config dict."""

    def __init__(self, raw: dict):
        self._raw = raw
        self._policies = {
            name: _parse_prune_policy(p)
            for name, p in raw.get("prune_policy", {}).items()
        }

    def _resolve_prune_policy(self, repo_entry: dict) -> ResticPruneKeepParams:
        name = repo_entry["prune_policy"]
        if name not in self._policies:
            raise ValueError(
                f"Prune policy '{name}' not found in "
                f"[prune_policy] section"
            )
        return self._policies[name]

    def _parse_repos(self, job_raw: dict) -> list[RepoConfig]:
        repos = []
        for r in job_raw.get("repositories", []):
            copy_dests = [
                CopyDestConfig(
                    repo_path=c["repo"],
                    password_file=Path(c["password_file"]),
                    prune_keep_params=self._resolve_prune_policy(c),
                )
                for c in r.get("copy_to", [])
            ]
            repos.append(RepoConfig(
                repo_path=r["repo_path"],
                password_file=Path(r["password_file"]),
                prune_keep_params=self._resolve_prune_policy(r),
                copy_destinations=copy_dests,
            ))
        return repos

    def _parse_volumes(self) -> dict[str, VolumeConfig]:
        volumes = {}
        for name, job in self._raw.get("volume", {}).items():
            volume_type = VolumeType(job["volume_type"])

            vg_name = None
            lv_name = None
            snapshot_size = None
            if volume_type in (VolumeType.LV_ROOT, VolumeType.LV_NONROOT):
                vg_name = job["vg_name"]
                lv_name = job["lv_name"]
                snapshot_size = job["snapshot_size"]

            volumes[name] = VolumeConfig(
                volume_type=volume_type,
                backup_source_path=job["backup_source_path"],
                exclude_paths=job.get("exclude_paths", []),
                repositories=self._parse_repos(job),
                vg_name=vg_name,
                lv_name=lv_name,
                snapshot_size=snapshot_size,
            )
        return volumes

    def _parse_snapshot_settings(self) -> SnapshotSettings:
        raw = self._raw.get("snapshot_settings", {})
        return SnapshotSettings(
            min_vg_free_after_snapshots=raw.get(
                "min_vg_free_after_snapshots", "1G"
            ),
            snapshot_cow_warn_percent=int(
                raw.get("snapshot_cow_warn_percent", 70)
            ),
        )

    def build(self) -> BackupConfig:
        return BackupConfig(
            prune_policies=self._policies,
            volumes=self._parse_volumes(),
            snapshot_settings=self._parse_snapshot_settings(),
        )
