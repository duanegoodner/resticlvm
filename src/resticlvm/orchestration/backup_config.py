"""Typed representation of a ResticLVM backup configuration file."""

from dataclasses import dataclass, field
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
class StandardPathJobConfig:
    """Config for a standard (non-LVM) backup job."""

    backup_source_path: str
    exclude_paths: list[str]
    repositories: list[RepoConfig]


@dataclass
class LvJobConfig:
    """Config for a logical-volume backup job."""

    vg_name: str
    lv_name: str
    snapshot_size: str
    backup_source_path: str
    exclude_paths: list[str]
    repositories: list[RepoConfig]


@dataclass
class BackupConfig:
    """Typed, fully-resolved backup configuration."""

    prune_policies: dict[str, ResticPruneKeepParams]
    standard_paths: dict[str, StandardPathJobConfig]
    logical_volume_roots: dict[str, LvJobConfig]
    logical_volume_nonroots: dict[str, LvJobConfig]


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

    def _parse_standard_paths(self) -> dict[str, StandardPathJobConfig]:
        return {
            name: StandardPathJobConfig(
                backup_source_path=job["backup_source_path"],
                exclude_paths=job.get("exclude_paths", []),
                repositories=self._parse_repos(job),
            )
            for name, job in self._raw.get("standard_path", {}).items()
        }

    def _parse_lv_jobs(self, section_key: str) -> dict[str, LvJobConfig]:
        return {
            name: LvJobConfig(
                vg_name=job["vg_name"],
                lv_name=job["lv_name"],
                snapshot_size=job["snapshot_size"],
                backup_source_path=job["backup_source_path"],
                exclude_paths=job.get("exclude_paths", []),
                repositories=self._parse_repos(job),
            )
            for name, job in self._raw.get(section_key, {}).items()
        }

    def build(self) -> BackupConfig:
        return BackupConfig(
            prune_policies=self._policies,
            standard_paths=self._parse_standard_paths(),
            logical_volume_roots=self._parse_lv_jobs(
                "logical_volume_root"
            ),
            logical_volume_nonroots=self._parse_lv_jobs(
                "logical_volume_nonroot"
            ),
        )
