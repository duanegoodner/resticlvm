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


def confirm_unique_repos(config: dict) -> dict[Path, ResticRepo]:
    """
    Ensure that all repos in the config are unique.
    """
    seen_repos = {}
    for category in config.keys():
        for job_name, job_config in config[category].items():
            repo = job_config["restic_repo"]
            if repo in seen_repos:
                raise ValueError(f"Duplicate repo detected: {repo}")
            seen_repos[repo] = ResticRepo(
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


def run_prune_shell_script(repo, password_file, prune_params):
    script_path = pkg_resources.files(scripts) / "prune_repo.sh"

    cmd = [
        "bash",
        str(script_path),
        repo,
        password_file,
        prune_params["prune_keep_last"],
        prune_params["prune_keep_daily"],
        prune_params["prune_keep_weekly"],
        prune_params["prune_keep_monthly"],
        prune_params["prune_keep_yearly"],
    ]

    try:
        subprocess.run(cmd, check=True, stdout=sys.stdout, stderr=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"❌ Prune failed for {repo}: {e}")
    except Exception as e:
        print(f"❌ Unexpected error during prune for {repo}: {e}")


def main():
    ensure_running_as_root()

    parser = argparse.ArgumentParser(description="Prune restic repos.")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to config file (.toml)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path)

    seen_repos = {}
    for category in config.keys():
        for job_name, job_config in config[category].items():
            repo = job_config["restic_repo"]
            if repo in seen_repos:
                print(f"❌ Error: Duplicate repo detected: {repo}")
                sys.exit(1)
            seen_repos[repo] = {
                "password_file": job_config["restic_password_file"],
                "prune_params": {
                    "prune_keep_last": str(job_config["prune_keep_last"]),
                    "prune_keep_daily": str(job_config["prune_keep_daily"]),
                    "prune_keep_weekly": str(job_config["prune_keep_weekly"]),
                    "prune_keep_monthly": str(
                        job_config["prune_keep_monthly"]
                    ),
                    "prune_keep_yearly": str(job_config["prune_keep_yearly"]),
                },
            }

    for repo, details in seen_repos.items():
        print(f"🧹 Pruning repo: {repo}")
        run_prune_shell_script(
            repo,
            details["password_file"],
            details["prune_params"],
        )


if __name__ == "__main__":
    main()
