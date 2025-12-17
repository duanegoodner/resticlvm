"""
CLI entry point for running backup jobs with ResticLVM.

Parses command-line arguments, loads the configured backup plan,
and executes backup jobs based on the specified filters.
"""

import argparse
from pathlib import Path

from resticlvm.orchestration.backup_plan import BackupPlan
from resticlvm.orchestration.data_classes import BackupJob
from resticlvm.orchestration.privileges import ensure_running_as_root


class BackupJobRunner:
    """Manages and runs a list of backup jobs."""

    def __init__(self, jobs: list[BackupJob]):
        """Initialize the BackupJobRunner.

        Args:
            jobs (list[BackupJob]): List of BackupJob instances to manage.
        """
        self.jobs = jobs

    def run_all(self, category: str = None, name: str = None):
        """Run all backup jobs, optionally filtering by category and/or job name.

        Args:
            category (str, optional): Backup category to filter by (e.g., 'standard_path').
            name (str, optional): Specific backup job name to run.
        """
        for job in self.jobs:
            if category and job.category != category:
                continue
            if name and job.name != name:
                continue
            job.run()


def main():
    """Parse CLI arguments and execute the backup plan."""
    ensure_running_as_root()

    parser = argparse.ArgumentParser(description="Run backup jobs.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be backed up without actually running.",
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Only run backups of this specific category.",
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Only run backups with this specific job name.",
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to configuration TOML file.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)

    plan = BackupPlan(config_path=config_path, dry_run=args.dry_run)
    runner = BackupJobRunner(plan.backup_jobs)
    runner.run_all(category=args.category, name=args.name)


if __name__ == "__main__":
    main()
