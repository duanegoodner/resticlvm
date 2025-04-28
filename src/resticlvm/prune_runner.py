#!/usr/bin/env python

import argparse
from pathlib import Path

from resticlvm.config_loader import load_config
from resticlvm.privileges import ensure_running_as_root
from resticlvm.restic_repo import confirm_unique_repos

# ─── Main ─────────────────────────────────────────────────────────


def main():
    ensure_running_as_root()

    parser = argparse.ArgumentParser(description="Prune restic repos.")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to config file (.toml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be pruned without actually pruning",
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Only prune repos in this backup category",
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Only prune repo matching this backup job name",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path)

    restic_repos = confirm_unique_repos(config=config)

    for (category, name), repo in restic_repos.items():
        if args.category and category != args.category:
            continue
        if args.name and name != args.name:
            continue

        repo.prune(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
