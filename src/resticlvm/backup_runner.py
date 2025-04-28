#!/usr/bin/env python

import argparse
import os
import subprocess
import sys
from pathlib import Path

from resticlvm.backup_plan import BackupPlan
from resticlvm.data_classes import BackupJob
from resticlvm.privileges import ensure_running_as_root


class BackupJobRunner:
    def __init__(self, jobs: list[BackupJob]):
        self.jobs = jobs

    def run_all(self, category: str = None, name: str = None):
        for job in self.jobs:
            if category and job.category != category:
                continue
            if name and job.name != name:
                continue
            job.run()


def main():
    ensure_running_as_root()

    parser = argparse.ArgumentParser(description="Run backup jobs.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be backed up without actually running",
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Only run backups of this specific category",
    )
    parser.add_argument(
        "--name", type=str, help="Only run backups with this specific job name"
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to configuration TOML file",
    )
    args = parser.parse_args()

    config_path = Path(args.config)

    plan = BackupPlan(config_path=config_path, dry_run=args.dry_run)
    runner = BackupJobRunner(plan.backup_jobs)
    runner.run_all(category=args.category, name=args.name)


if __name__ == "__main__":
    main()
