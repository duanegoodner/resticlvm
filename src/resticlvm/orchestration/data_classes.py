"""
Defines core data classes used for running backup jobs in ResticLVM,
including token-to-config mappings and job execution logic.
"""

import importlib.resources as pkg_resources
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from resticlvm import scripts


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

    @property
    def cmd(self) -> list[str]:
        """Build the full shell command to run the backup job.

        Returns:
            list[str]: Full command as a list suitable for subprocess.
        """
        return ["bash", str(self.script_path)] + self.args_list

    def run(self):
        """Execute the backup job by running the associated script.

        Raises:
            subprocess.CalledProcessError: If the script exits with an error code.
            FileNotFoundError: If the script file is missing.
            Exception: For any other unexpected errors during execution.
        """
        print(f"▶️ Running backup job: [{self.category}.{self.name}]")
        try:
            subprocess.run(
                args=self.cmd,
                check=True,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            print(f"✅ Backup [{self.category}.{self.name}] completed.\n")
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed [{self.category}.{self.name}]: {e}")
        except FileNotFoundError as e:
            print(f"❌ Script not found [{self.category}.{self.name}]: {e}")
        except Exception as e:
            print(f"❌ Unexpected error [{self.category}.{self.name}]: {e}")
