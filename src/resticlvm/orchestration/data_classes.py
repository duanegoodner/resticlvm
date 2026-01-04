"""
Defines core data classes used for running backup jobs in ResticLVM,
including token-to-config mappings and job execution logic.
"""

import importlib.resources as pkg_resources
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from resticlvm import scripts
from resticlvm.orchestration.restic_repo import ResticRepo


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
    repositories: list[ResticRepo] = field(default_factory=list)
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

    def get_args_list_for_repo(self, repo: ResticRepo) -> list[str]:
        """Construct script arguments for a specific repository.

        Args:
            repo (ResticRepo): The repository to generate arguments for.

        Returns:
            list[str]: List of script argument strings including repo and password.
        """
        args = []
        for pair in self.script_token_config_key_pairs:
            # Skip repo and password tokens - we'll add them from ResticRepo
            if pair.token in ["-r", "-p"]:
                continue
            args += self.get_arg_entry(pair)
        
        # Add repository-specific arguments
        args += ["-r", str(repo.repo_path)]
        args += ["-p", str(repo.password_file)]
        
        return args

    @property
    def args_list(self) -> list[str]:
        """Construct the full list of script arguments for the backup job.

        Note: For multi-repo jobs, use get_args_list_for_repo() instead.
        This property is maintained for backward compatibility.

        Returns:
            list[str]: List of script argument strings.
        """
        args = []
        for pair in self.script_token_config_key_pairs:
            args += self.get_arg_entry(pair)
        return args

    @property
    def script_path(self) -> Path:
        """Get the resolved filesystem path to the backup script.

        Returns:
            Path: Filesystem path to the associated shell script.
        """
        return pkg_resources.files(scripts) / self.script_name

    def get_cmd_for_repo(self, repo: ResticRepo) -> list[str]:
        """Build the shell command for a specific repository.

        Args:
            repo (ResticRepo): The repository to build the command for.

        Returns:
            list[str]: Full command as a list suitable for subprocess.
        """
        return ["bash", str(self.script_path)] + self.get_args_list_for_repo(repo)

    @property
    def cmd(self) -> list[str]:
        """Build the full shell command to run the backup job.

        Note: For multi-repo jobs, use get_cmd_for_repo() instead.
        This property is maintained for backward compatibility.

        Returns:
            list[str]: Full command as a list suitable for subprocess.
        """
        return ["bash", str(self.script_path)] + self.args_list

    def run(self):
        """Execute the backup job by running the script for each repository.

        For jobs with multiple repositories, the backup is performed sequentially
        for each repository. Continues attempting all repositories even if some fail.

        Raises:
            subprocess.CalledProcessError: If the script exits with an error code.
            FileNotFoundError: If the script file is missing.
            Exception: For any other unexpected errors during execution.
        """
        if not self.repositories:
            print(f"⚠️  Warning: No repositories configured for [{self.category}.{self.name}]")
            return
        
        print(f"▶️  Running backup job: [{self.category}.{self.name}] -> {len(self.repositories)} repo(s)")
        
        failed_repos = []
        successful_repos = []
        
        for i, repo in enumerate(self.repositories, 1):
            repo_label = f"[{self.category}.{self.name}] repo {i}/{len(self.repositories)}: {repo.repo_path}"
            print(f"\n▶️  Backing up to {repo_label}")
            
            try:
                cmd = self.get_cmd_for_repo(repo)
                subprocess.run(
                    args=cmd,
                    check=True,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
                print(f"✅ Backup to {repo.repo_path} completed.")
                successful_repos.append(repo.repo_path)
            except subprocess.CalledProcessError as e:
                print(f"❌ Command failed for {repo.repo_path}: {e}")
                failed_repos.append(repo.repo_path)
            except FileNotFoundError as e:
                print(f"❌ Script not found for {repo.repo_path}: {e}")
                failed_repos.append(repo.repo_path)
            except Exception as e:
                print(f"❌ Unexpected error for {repo.repo_path}: {e}")
                failed_repos.append(repo.repo_path)
        
        # Print summary
        print(f"\n{'='*70}")
        print(f"Backup job [{self.category}.{self.name}] summary:")
        print(f"  ✅ Successful: {len(successful_repos)}/{len(self.repositories)}")
        print(f"  ❌ Failed: {len(failed_repos)}/{len(self.repositories)}")
        if failed_repos:
            print(f"\nFailed repositories:")
            for repo_path in failed_repos:
                print(f"  - {repo_path}")
        print(f"{'='*70}\n")
