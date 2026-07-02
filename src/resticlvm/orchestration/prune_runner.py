"""
CLI entry point for pruning Restic repositories with ResticLVM.

Parses command-line arguments, loads the configured repositories,
and prunes snapshots according to the configured retention policies.
"""

import argparse
from pathlib import Path

from resticlvm import __version__
from resticlvm.orchestration.backup_config import BackupConfigFactory
from resticlvm.orchestration.backup_plan import _to_restic_repo
from resticlvm.orchestration.config_loader import load_config
from resticlvm.orchestration.privileges import ensure_running_as_root


def run(args):
    """Execute prune operations from pre-parsed arguments.

    Args:
        args: Namespace with config, dry_run, category, and name attributes.
    """
    config_path = Path(args.config)
    raw = load_config(config_path)
    config = BackupConfigFactory(raw).build()

    _SECTIONS = [
        ("standard_path", config.standard_paths),
        ("logical_volume_root", config.logical_volume_roots),
        ("logical_volume_nonroot", config.logical_volume_nonroots),
    ]

    for category, jobs in _SECTIONS:
        if args.category and category != args.category:
            continue
        for name, job_cfg in jobs.items():
            if args.name and name != args.name:
                continue
            for repo_cfg in job_cfg.repositories:
                repo = _to_restic_repo(repo_cfg)
                repo.prune(dry_run=args.dry_run)


def main():
    """Parse CLI arguments and execute prune operations for Restic repositories."""
    parser = argparse.ArgumentParser(description="Prune Restic repositories.")
    parser.add_argument(
        "--version",
        action="version",
        version=f"resticlvm {__version__}",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to config file (.toml).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be pruned without actually pruning.",
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Only prune repos in this backup category.",
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Only prune the repo matching this backup job name.",
    )
    args = parser.parse_args()

    # Root check happens after argument parsing so --version / --help work
    # without elevation.
    ensure_running_as_root()

    run(args)


if __name__ == "__main__":
    main()
