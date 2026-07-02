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

    for name, vol_cfg in config.volumes.items():
        if args.category and vol_cfg.volume_type.value != args.category:
            continue
        if args.name and name != args.name:
            continue
        for repo_cfg in vol_cfg.repositories:
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
        help="Only prune repos with this volume type.",
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Only prune the repo matching this volume name.",
    )
    args = parser.parse_args()

    ensure_running_as_root()

    run(args)


if __name__ == "__main__":
    main()
