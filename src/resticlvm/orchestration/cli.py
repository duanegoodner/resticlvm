"""Unified CLI entry point for ResticLVM."""

import argparse
import sys

from resticlvm import __version__
from resticlvm.orchestration.privileges import ensure_running_as_root


def _add_common_arguments(parser):
    parser.add_argument(
        "--config",
        required=True,
        help="Path to configuration TOML file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without actually running.",
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Only operate on this backup category.",
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Only operate on this specific job name.",
    )


def main():
    parser = argparse.ArgumentParser(
        prog="rlvm",
        description="ResticLVM — config-driven LVM-snapshot backups with Restic.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"resticlvm {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")

    backup_parser = subparsers.add_parser(
        "backup", help="Run backup jobs."
    )
    _add_common_arguments(backup_parser)

    prune_parser = subparsers.add_parser(
        "prune", help="Prune Restic snapshots."
    )
    _add_common_arguments(prune_parser)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    ensure_running_as_root()

    if args.command == "backup":
        from resticlvm.orchestration.backup_runner import run as run_backup

        run_backup(args)
    elif args.command == "prune":
        from resticlvm.orchestration.prune_runner import run as run_prune

        run_prune(args)


if __name__ == "__main__":
    main()
