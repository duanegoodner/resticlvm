import importlib.resources as pkg_resources
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from resticlvm import scripts


@dataclass
class TokenConfigKeyPair:
    token: str
    config_key: str

    @classmethod
    def from_token_key_map(cls, token_key_map: dict[str, str]):
        return [
            cls(token, config_key)
            for token, config_key in token_key_map.items()
        ]


@dataclass
class BackupJob:
    script_name: str
    script_token_config_key_pairs: list[TokenConfigKeyPair]
    config: dict
    name: str
    category: str
    dry_run: bool = False

    def get_arg_entry(self, pair: TokenConfigKeyPair) -> list[str]:
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
        args = []
        for pair in self.script_token_config_key_pairs:
            args += self.get_arg_entry(pair)
        return args

    @property
    def script_path(self) -> Path:
        return pkg_resources.files(scripts) / self.script_name

    @property
    def cmd(self) -> list[str]:
        return ["bash", str(self.script_path)] + self.args_list

    def run(self):
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
