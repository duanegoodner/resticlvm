"""
CLI entry point for pruning Restic repositories with ResticLVM.

Parses command-line arguments, loads the configured repositories,
and prunes snapshots according to the configured retention policies.
"""

import argparse
from pathlib import Path

from resticlvm.orchestration.config_loader import load_config
from resticlvm.orchestration.privileges import ensure_running_as_root
from resticlvm.orchestration.restic_repo import confirm_unique_repos


def main():
    """Parse CLI arguments and execute prune operations for Restic repositories.

    Raises:
        PermissionError: If the user does not have root privileges.
    """
    ensure_running_as_root()

    parser = argparse.ArgumentParser(description="Prune Restic repositories.")
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

    config_path = Path(args.config)
    config = load_config(config_path)

    restic_repos = confirm_unique_repos(config=config)

    for (category, name), repo_list in restic_repos.items():
        if args.category and category != args.category:
            continue
        if args.name and name != args.name:
            continue

        # Prune each repository in the job
        for repo in repo_list:
            repo.prune(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
