#!/usr/bin/env python

import argparse
import importlib.resources as pkg_resources
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from resticlvm import scripts
from resticlvm.config_loader import load_config
from resticlvm.privileges import ensure_running_as_root

# ─── Data Classes ─────────────────────────────────────────────────


@dataclass
class ResticPruneKeepParams:
    last: int
    daily: int
    weekly: int
    monthly: int
    yearly: int


@dataclass
class ResticRepo:
    repo_path: Path
    password_file: Path
    prune_keep_params: ResticPruneKeepParams

    def prune(self, dry_run: bool = False):
        script_path = pkg_resources.files(scripts) / "prune_repo.sh"

        cmd = [
            "bash",
            str(script_path),
            str(self.repo_path),
            str(self.password_file),
            str(self.prune_keep_params.last),
            str(self.prune_keep_params.daily),
            str(self.prune_keep_params.weekly),
            str(self.prune_keep_params.monthly),
            str(self.prune_keep_params.yearly),
        ]
        if dry_run:
            cmd.append("--dry-run")

        print(f"▶️ Pruning repo {self.repo_path} (dry-run={dry_run})")

        try:
            subprocess.run(
                cmd, check=True, stdout=sys.stdout, stderr=sys.stderr
            )
            print(f"✅ Prune completed for {self.repo_path}\n")
        except subprocess.CalledProcessError as e:
            print(f"❌ Prune failed for {self.repo_path}: {e}")
        except Exception as e:
            print(
                f"❌ Unexpected error during prune for {self.repo_path}: {e}"
            )


# ─── Helpers ──────────────────────────────────────────────────────


def confirm_unique_repos(config: dict) -> dict[tuple[str, str], ResticRepo]:
    """
    Ensure that all repos in the config are unique.
    Returns a mapping of (category, job_name) -> ResticRepo.
    """
    seen_repos = {}
    repo_paths_seen = set()

    for category in config.keys():
        for job_name, job_config in config[category].items():
            repo = job_config["restic_repo"]
            if repo in repo_paths_seen:
                raise ValueError(f"Duplicate repo detected: {repo}")
            repo_paths_seen.add(repo)

            seen_repos[(category, job_name)] = ResticRepo(
                repo_path=Path(repo),
                password_file=Path(job_config["restic_password_file"]),
                prune_keep_params=ResticPruneKeepParams(
                    last=int(job_config["prune_keep_last"]),
                    daily=int(job_config["prune_keep_daily"]),
                    weekly=int(job_config["prune_keep_weekly"]),
                    monthly=int(job_config["prune_keep_monthly"]),
                    yearly=int(job_config["prune_keep_yearly"]),
                ),
            )
    return seen_repos


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
        help="Only prune repos in this backup category (e.g. logical_volume_root)",
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Only prune repo matching this backup job name (e.g. lv_root)",
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
