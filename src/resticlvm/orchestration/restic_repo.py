"""
Defines classes and utilities for representing Restic repositories
and managing prune operations based on backup configurations.
"""

import importlib.resources as pkg_resources
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from resticlvm import scripts
from resticlvm.orchestration.credentials import (
    B2CredentialsError,
    load_b2_credentials,
    repo_uses_b2,
)
from resticlvm.orchestration.terminal import preserved_terminal


@dataclass
class ResticPruneKeepParams:
    """Stores Restic prune retention parameters."""

    last: int
    daily: int
    weekly: int
    monthly: int
    yearly: int


@dataclass
class CopyDestination:
    """Represents a destination repository for restic copy operations."""

    repo_path: str
    password_file: Path
    prune_keep_params: ResticPruneKeepParams


@dataclass
class ResticRepo:
    """Represents a Restic repository and associated pruning settings."""

    repo_path: Path
    password_file: Path
    prune_keep_params: ResticPruneKeepParams
    copy_destinations: list['CopyDestination'] = None

    def __post_init__(self):
        """Initialize copy_destinations as empty list if None."""
        if self.copy_destinations is None:
            self.copy_destinations = []

    def prune(self, dry_run: bool = False):
        """Prune snapshots in the Restic repository.

        Args:
            dry_run (bool, optional): If True, perform a dry-run without
                actually deleting any snapshots. Defaults to False.

        Raises:
            subprocess.CalledProcessError: If the Restic prune command fails.
            Exception: For unexpected errors during the prune operation.
        """
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

        env = os.environ.copy()
        env.setdefault('SSH_AUTH_SOCK', '/root/.ssh/ssh-agent.sock')

        if repo_uses_b2(self.repo_path):
            try:
                load_b2_credentials(env)
            except B2CredentialsError as e:
                print(f"❌ B2 credentials for {self.repo_path}: {e}")
                return

        try:
            # Pruning a remote repo runs ssh; guard the terminal (issue #57).
            with preserved_terminal():
                subprocess.run(
                    cmd, check=True, stdout=sys.stdout, stderr=sys.stderr,
                    env=env,
                )
            print(f"✅ Prune completed for {self.repo_path}\n")
        except subprocess.CalledProcessError as e:
            print(f"❌ Prune failed for {self.repo_path}: {e}")
        except Exception as e:
            print(
                f"❌ Unexpected error during prune for {self.repo_path}: {e}"
            )


