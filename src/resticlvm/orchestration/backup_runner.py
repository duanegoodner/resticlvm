"""
CLI entry point for running backup jobs with ResticLVM.

Parses command-line arguments, loads the configured backup plan,
and executes backup jobs based on the specified filters.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

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

    def run_all(
        self, category: Optional[str] = None, name: Optional[str] = None
    ) -> int:
        """Run all backup jobs, optionally filtering by category and/or job name.

        Each job runs in isolation: a failure in one does not stop the others. A
        summary is printed at the end naming any failed jobs and copy operations.

        Args:
            category (str, optional): Backup category to filter by (e.g., 'standard_path').
            name (str, optional): Specific backup job name to run.

        Returns:
            int: The number of jobs that failed (a failed backup script or any
            failed copy operation counts as a failed job). 0 means everything
            succeeded.
        """
        results = []
        for job in self.jobs:
            if category and job.category != category:
                continue
            if name and job.name != name:
                continue
            results.append(job.run())

        failures = [r for r in results if not r.ok]
        print("\n──────── Backup run summary ────────")
        print(f"  jobs run: {len(results)}   failed: {len(failures)}")
        for r in failures:
            if not r.script_ok:
                print(f"  ❌ {r.category}.{r.name}: backup script failed")
            for dest in r.failed_copies:
                print(f"  ❌ {r.category}.{r.name}: copy to {dest} failed")

        return len(failures)


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
    failure_count = runner.run_all(category=args.category, name=args.name)
    if failure_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
