"""
CLI entry point for pruning Restic repositories with ResticLVM.

Parses command-line arguments, loads the configured repositories,
and prunes snapshots according to the configured retention policies.
"""

import argparse
from pathlib import Path

from resticlvm import __version__
from resticlvm.orchestration.config_loader import load_config
from resticlvm.orchestration.privileges import ensure_running_as_root
from resticlvm.orchestration.restic_repo import confirm_unique_repos


def main():
    """Parse CLI arguments and execute prune operations for Restic repositories.

    Raises:
        PermissionError: If the user does not have root privileges.
    """
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

    config_path = Path(args.config)
    config = load_config(config_path)

    restic_repos = confirm_unique_repos(config=config)

    for (category, name), repos in restic_repos.items():
        if args.category and category != args.category:
            continue
        if args.name and name != args.name:
            continue

        for repo in repos:
            repo.prune(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
