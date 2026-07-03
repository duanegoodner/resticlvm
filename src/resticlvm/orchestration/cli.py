"""Unified CLI entry point for ResticLVM."""

import argparse
import os
import sys
from pathlib import Path

from resticlvm import __version__
from resticlvm.orchestration.privileges import ensure_running_as_root

DEFAULT_CONFIG_PATH = Path("/etc/resticlvm/backup.toml")
CONFIG_ENV_VAR = "RESTICLVM_CONFIG"


def resolve_config(explicit: str | None) -> Path:
    """Return the config path from --config, env var, or default.

    Precedence: explicit --config flag > $RESTICLVM_CONFIG > default path.
    Exits with a clear message if the resolved path does not exist.
    """
    if explicit is not None:
        path = Path(explicit)
        if not path.is_file():
            sys.exit(f"rlvm: config file not found: {path}")
        return path

    from_env = os.environ.get(CONFIG_ENV_VAR)
    if from_env is not None:
        path = Path(from_env)
        if not path.is_file():
            sys.exit(
                f"rlvm: config file not found: {path}"
                f" (from ${CONFIG_ENV_VAR})"
            )
        return path

    if DEFAULT_CONFIG_PATH.is_file():
        return DEFAULT_CONFIG_PATH

    sys.exit(
        f"rlvm: no config file found. Provide one with --config,"
        f" set ${CONFIG_ENV_VAR},"
        f" or place a config at {DEFAULT_CONFIG_PATH}"
    )


def _add_common_arguments(parser):
    parser.add_argument(
        "--config",
        default=None,
        help=(
            "Path to configuration TOML file."
            f" Default: {DEFAULT_CONFIG_PATH}"
            f" (override with ${CONFIG_ENV_VAR})."
        ),
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

    args.config = str(resolve_config(args.config))

    ensure_running_as_root()

    if args.command == "backup":
        from resticlvm.orchestration.backup_runner import run as run_backup

        run_backup(args)
    elif args.command == "prune":
        from resticlvm.orchestration.prune_runner import run as run_prune

        run_prune(args)


if __name__ == "__main__":
    main()
