"""Soft validation checks for a parsed BackupConfig."""

import logging
from posixpath import basename as posix_basename

from resticlvm.orchestration.backup_config import BackupConfig

logger = logging.getLogger(__name__)


def repo_name_from_path(repo_path: str) -> str:
    """Extract the final path component from a repo_path.

    Handles local paths, sftp:user@host:/path, and s3:host/path.
    """
    path_part = repo_path
    if ":" in repo_path:
        path_part = repo_path.rsplit(":", maxsplit=1)[1]
    return posix_basename(path_part.rstrip("/"))


def validate_repo_names(config: BackupConfig) -> list[str]:
    """Warn when repos within a volume have mismatched final path components.

    Checks both primary repositories and their copy_to destinations.
    Returns a list of warning strings (empty if everything is consistent).
    """
    warnings: list[str] = []

    for vol_name, vol_cfg in config.volumes.items():
        all_paths: list[str] = []
        for repo in vol_cfg.repositories:
            all_paths.append(repo.repo_path)
            for dest in repo.copy_destinations:
                all_paths.append(dest.repo_path)

        if len(all_paths) <= 1:
            continue

        names = {p: repo_name_from_path(p) for p in all_paths}
        unique_names = set(names.values())

        if len(unique_names) > 1:
            detail = ", ".join(
                f"{path} -> '{name}'" for path, name in names.items()
            )
            warnings.append(
                f"Volume '{vol_name}': repo names differ: {detail}"
            )

    return warnings


def validate_config(config: BackupConfig) -> list[str]:
    """Run all soft validation checks. Returns collected warnings."""
    return validate_repo_names(config)


def warn_on_validation_issues(config: BackupConfig) -> None:
    """Run validation and log any warnings."""
    for warning in validate_config(config):
        logger.warning(warning)
