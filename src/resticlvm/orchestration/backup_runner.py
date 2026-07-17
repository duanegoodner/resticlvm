"""
CLI entry point for running backup jobs with ResticLVM.

Parses command-line arguments, loads the configured backup plan,
and executes backup jobs based on the specified filters.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from resticlvm import __version__
from resticlvm.orchestration.backup_config import SnapshotSettings
from resticlvm.orchestration.backup_plan import BackupPlan
from resticlvm.orchestration.data_classes import BackupJob
from resticlvm.orchestration.privileges import ensure_running_as_root
from resticlvm.orchestration.snapshot_coordinator import SnapshotCoordinator

_LV_CATEGORIES = {"lv_root", "lv_nonroot"}


class BackupJobRunner:
    """Manages and runs a list of backup jobs."""

    def __init__(
        self,
        jobs: list[BackupJob],
        snapshot_settings: SnapshotSettings | None = None,
    ):
        self.jobs = jobs
        self._snap_settings = snapshot_settings or SnapshotSettings()

    def run_all(
        self, category: Optional[str] = None, name: Optional[str] = None
    ) -> int:
        """Run all backup jobs, optionally filtering by category and/or job name.

        LV-backed volumes use batch snapshot coordination (issue #84): all
        snapshots are created before any backup runs, reducing the cross-LV
        time delta to milliseconds. Copy operations for LV jobs are deferred
        until after snapshot teardown to minimize snapshot lifetime.

        Each job runs in isolation: a failure in one does not stop the others. A
        summary is printed at the end naming any failed jobs and copy operations.

        Returns:
            int: The number of jobs that failed.
        """
        active_jobs = [
            j for j in self.jobs
            if (not category or j.category == category)
            and (not name or j.name == name)
        ]

        lv_jobs = [j for j in active_jobs if j.category in _LV_CATEGORIES]
        non_lv_jobs = [j for j in active_jobs if j.category not in _LV_CATEGORIES]

        results = []
        deferred_copy_jobs = []

        if lv_jobs:
            dry_run = lv_jobs[0].dry_run
            coord = SnapshotCoordinator(
                lv_jobs,
                dry_run=dry_run,
                min_vg_free_after_snapshots=self._snap_settings.min_vg_free_after_snapshots,
                snapshot_cow_warn_percent=self._snap_settings.snapshot_cow_warn_percent,
            )

            with coord:
                coord.create_all()

                for job in lv_jobs:
                    mount = coord.get_mount_point(job.name)
                    result = job.run(snapshot_mount=mount, defer_copies=True)
                    results.append(result)
                    if result.script_ok:
                        deferred_copy_jobs.append(job)

            # Snapshots are now torn down — run deferred copies
            for job in deferred_copy_jobs:
                failed = job.run_deferred_copies()
                if failed:
                    for r in results:
                        if r.name == job.name and r.category == job.category:
                            r.failed_copies = failed
                            break

        for job in non_lv_jobs:
            results.append(job.run())

        self._print_summary(results)
        return len([r for r in results if not r.ok])

    @staticmethod
    def _print_summary(results):
        failures = [r for r in results if not r.ok]
        total = len(results)
        print()
        if failures:
            bar = "!" * 64
            print(bar)
            print(f"  ⚠️  BACKUP FAILED — {len(failures)} of {total} job(s) did NOT succeed")
            print(bar)
            for r in failures:
                if not r.script_ok:
                    print(f"  ❌ {r.category}.{r.name}: backup failed")
                for dest in r.failed_copies:
                    print(f"  ❌ {r.category}.{r.name}: copy to {dest} failed")
            print(bar)
        else:
            print("──────── Backup run summary ────────")
            print(f"  ✅ All {total} job(s) completed successfully.")


def run(args):
    """Execute the backup plan from pre-parsed arguments.

    Args:
        args: Namespace with config, dry_run, category, and name attributes.
    """
    config_path = Path(args.config)

    plan = BackupPlan(config_path=config_path, dry_run=args.dry_run)
    runner = BackupJobRunner(
        plan.backup_jobs,
        snapshot_settings=plan.snapshot_settings,
    )
    failure_count = runner.run_all(category=args.category, name=args.name)
    if failure_count:
        sys.exit(1)


def main():
    """Parse CLI arguments and execute the backup plan."""
    parser = argparse.ArgumentParser(description="Run backup jobs.")
    parser.add_argument(
        "--version",
        action="version",
        version=f"resticlvm {__version__}",
    )
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

    # Root check happens after argument parsing so --version / --help work
    # without elevation.
    ensure_running_as_root()

    run(args)


if __name__ == "__main__":
    main()
