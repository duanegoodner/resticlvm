"""
Defines core data classes used for running backup jobs in ResticLVM,
including token-to-config mappings and job execution logic.
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


@dataclass
class JobResult:
    """Outcome of a single BackupJob.run()."""

    category: str
    name: str
    script_ok: bool  # did the backup script itself succeed?
    failed_copies: list  # copy-destination repo_paths that failed (empty if all ok)

    @property
    def ok(self) -> bool:
        """True only if the backup script and all copy operations succeeded."""
        return self.script_ok and not self.failed_copies


@dataclass
class TokenConfigKeyPair:
    """Represents a mapping between a script token and a config file key."""

    token: str
    config_key: str

    @classmethod
    def from_token_key_map(cls, token_key_map: dict[str, str]):
        """Create a list of TokenConfigKeyPair instances from a token-key map.

        Args:
            token_key_map (dict[str, str]): Mapping of CLI tokens to config keys.

        Returns:
            list[TokenConfigKeyPair]: List of generated TokenConfigKeyPair objects.
        """
        return [
            cls(token, config_key)
            for token, config_key in token_key_map.items()
        ]


@dataclass
class BackupJob:
    """Represents a backup job to be executed via a shell script."""

    script_name: str
    script_token_config_key_pairs: list[TokenConfigKeyPair]
    config: dict
    name: str
    category: str
    repositories: list
    dry_run: bool = False

    def get_arg_entry(self, pair: TokenConfigKeyPair) -> list[str]:
        """Generate CLI arguments for a given token-config pair.

        Args:
            pair (TokenConfigKeyPair): The token-config mapping for a script argument.

        Returns:
            list[str]: A list containing the token and its associated value.

        Raises:
            TypeError: If the config value is of an unsupported type.
        """
        value = self.config[pair.config_key]
        if isinstance(value, list):
            return [pair.token, " ".join(value)]
        elif isinstance(value, (str, bool, int, float)):
            return [
                pair.token,
                str(value).lower() if isinstance(value, bool) else str(value),
            ]
        else:
            raise TypeError(
                f"Unsupported type for config key {pair.config_key}: {type(value)}"
            )

    @property
    def args_list(self) -> list[str]:
        """Construct the full list of script arguments for the backup job.

        Returns:
            list[str]: List of script argument strings.
        """
        args = []
        
        # Add non-repo arguments first (those not -r or -p)
        for pair in self.script_token_config_key_pairs:
            if pair.token not in ["-r", "-p"]:
                args += self.get_arg_entry(pair)
        
        # Add all repositories (multiple -r and -p pairs)
        for repo in self.repositories:
            args += ["-r", str(repo.repo_path)]
            args += ["-p", str(repo.password_file)]

        if self.dry_run:
            args.append("--dry-run")

        return args

    @property
    def script_path(self) -> Path:
        """Get the resolved filesystem path to the backup script.

        Returns:
            Path: Filesystem path to the associated shell script.
        """
        return pkg_resources.files(scripts) / self.script_name

    @property
    def cmd(self) -> list[str]:
        """Build the full shell command to run the backup job.

        Returns:
            list[str]: Full command as a list suitable for subprocess.
        """
        return ["bash", str(self.script_path)] + self.args_list

    def _uses_b2(self) -> bool:
        """True if any repository or copy destination targets a B2 (s3:) repo."""
        for repo in self.repositories:
            if repo_uses_b2(repo.repo_path):
                return True
            for dest in (repo.copy_destinations or []):
                if repo_uses_b2(dest.repo_path):
                    return True
        return False

    def run(self) -> "JobResult":
        """Execute the backup job by running the associated script.

        Failures are caught (not raised) so that one failed job does not abort the
        others; the outcome is reported via the returned JobResult instead. Copy
        operations are only attempted when the backup script itself succeeds.

        Returns:
            JobResult: The outcome of this job — whether the backup script
            succeeded and which copy destinations (if any) failed.
        """
        repo_count = len(self.repositories)
        print(f"▶️  Running backup job: [{self.category}.{self.name}] → {repo_count} repo(s)")

        # Prepare environment with SSH agent socket for SFTP repositories.
        # Respect an SSH_AUTH_SOCK already set by the caller; only fall back to
        # the conventional root agent socket when none is provided.
        env = os.environ.copy()
        env.setdefault('SSH_AUTH_SOCK', '/root/.ssh/ssh-agent.sock')

        # Load B2 (S3-compatible) credentials only if this job targets a B2 repo.
        # Non-B2 jobs run without any credentials present.
        if self._uses_b2():
            try:
                load_b2_credentials(env)
            except B2CredentialsError as e:
                print(f"❌ B2 credentials [{self.category}.{self.name}]: {e}")
                return JobResult(
                    category=self.category,
                    name=self.name,
                    script_ok=False,
                    failed_copies=[],
                )

        try:
            subprocess.run(
                args=self.cmd,
                check=True,
                stdout=sys.stdout,
                stderr=sys.stderr,
                env=env,
            )
            print(f"✅ Backup [{self.category}.{self.name}] completed.\n")

            # After successful backup, copy to remote destinations
            failed_copies = self._run_copy_operations(env)
            return JobResult(
                category=self.category,
                name=self.name,
                script_ok=True,
                failed_copies=failed_copies,
            )

        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed [{self.category}.{self.name}]: {e}")
        except FileNotFoundError as e:
            print(f"❌ Script not found [{self.category}.{self.name}]: {e}")

        return JobResult(
            category=self.category,
            name=self.name,
            script_ok=False,
            failed_copies=[],
        )

    def _run_copy_operations(self, env: dict) -> list:
        """Execute copy operations for repositories with copy_to destinations.

        Args:
            env (dict): Environment variables to pass to subprocess.

        Returns:
            list: Copy-destination repo_paths that failed (empty if all succeeded).
        """
        failed_copies = []
        for repo in self.repositories:
            if not repo.copy_destinations:
                continue

            for copy_dest in repo.copy_destinations:
                print(f"🔄 Copying from {repo.repo_path} to {copy_dest.repo_path}...")

                copy_script = pkg_resources.files(scripts) / "copy_repo.sh"

                cmd = [
                    "bash",
                    str(copy_script),
                    "-s", str(repo.repo_path),
                    "-p", str(repo.password_file),
                    "-d", str(copy_dest.repo_path),
                    "-q", str(copy_dest.password_file),
                ]
                if self.dry_run:
                    cmd.append("-n")

                try:
                    subprocess.run(
                        args=cmd,
                        check=True,
                        stdout=sys.stdout,
                        stderr=sys.stderr,
                        env=env,
                    )
                    print(f"✅ Copy to {copy_dest.repo_path} completed.\n")
                except subprocess.CalledProcessError as e:
                    print(f"❌ Copy to {copy_dest.repo_path} failed: {e}\n")
                    failed_copies.append(copy_dest.repo_path)
        return failed_copies
