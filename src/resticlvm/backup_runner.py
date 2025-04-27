import importlib.resources as pkg_resources
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from resticlvm import scripts
from resticlvm.config_loader import load_config


@dataclass
class TokenConfigKeyPair:
    token: str
    config_key: str


@dataclass
class BackupJobResources:
    script_name: str
    token_key_map: dict[str, str]


@dataclass
class BackupJob:
    script_name: str
    script_token_config_key_pairs: list[TokenConfigKeyPair]
    config: dict

    def get_arg_entry(self, pair: TokenConfigKeyPair) -> list[str]:
        result = [pair.token]
        config_val = self.config[pair.config_key]

        if isinstance(config_val, list):
            result.append(" ".join(config_val))
        else:
            result.append(
                str(config_val).lower()
                if isinstance(config_val, bool)
                else str(config_val)
            )

        return result

    @property
    def args_list(self) -> list[str]:
        return [
            arg
            for pair in self.script_token_config_key_pairs
            for arg in self.get_arg_entry(pair)
        ]

    @property
    def script_path(self) -> Path:
        return pkg_resources.files(scripts) / self.script_name

    @property
    def cmd(self) -> list[str]:
        return ["bash", str(self.script_path)] + self.args_list

    def run(self):
        print(f"🛠️ Running backup job using script: {self.script_name}")
        try:
            subprocess.run(
                self.cmd, check=True, stdout=sys.stdout, stderr=sys.stderr
            )
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed with error: {e}")
        except FileNotFoundError as e:
            print(f"❌ Script not found: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")


class BackupPlan:

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.full_config = load_config(config_path)

    @staticmethod
    def _standard_path_token_key_map() -> dict[str, str]:
        return {
            "-r": "restic_repo",
            "-p": "restic_password_file",
            "-s": "backup_source_path",
            "-e": "exclude_paths",
            "-m": "remount_readonly",
        }

    @staticmethod
    def _logical_volume_token_key_map() -> dict[str, str]:
        return {
            "-g": "vg_name",
            "-l": "lv_name",
            "-z": "snapshot_size",
            "-r": "restic_repo",
            "-p": "restic_password_file",
            "-s": "backup_source_path",
            "-e": "exclude_paths",
        }

    @staticmethod
    def _build_script_token_config_key_pairs(
        mapping: dict[str, str],
    ) -> list[TokenConfigKeyPair]:
        return [
            TokenConfigKeyPair(token, config_key)
            for token, config_key in mapping.items()
        ]

    @property
    def _resource_dispatch(self) -> dict[str, BackupJobResources]:
        return {
            "standard_path": BackupJobResources(
                script_name="backup_path.sh",
                token_key_map=self._standard_path_token_key_map(),
            ),
            "logical_volume_root": BackupJobResources(
                script_name="backup_lv_root.sh",
                token_key_map=self._logical_volume_token_key_map(),
            ),
            "logical_volume_nonroot": BackupJobResources(
                script_name="backup_lv_nonroot.sh",
                token_key_map=self._logical_volume_token_key_map(),
            ),
        }

    @property
    def _allowed_job_categories(self) -> list[str]:
        return list(self._resource_dispatch.keys())

    def create_backup_job(self, category: str, name: str) -> BackupJob:
        if category not in self._allowed_job_categories:
            raise ValueError(f"Invalid backup category: {category}")

        resources = self._resource_dispatch[category]
        config = self.full_config[category][name]

        return BackupJob(
            script_name=resources.script_name,
            script_token_config_key_pairs=self._build_script_token_config_key_pairs(
                resources.token_key_map
            ),
            config=config,
        )

    @property
    def backup_jobs(self) -> list[BackupJob]:
        return [
            self.create_backup_job(category, job_name)
            for category in self.full_config
            for job_name in self.full_config[category]
        ]

    def run_all_jobs(self):
        print(f"🚀 Starting all backup jobs from {self.config_path}")
        for job in self.backup_jobs:
            job.run()


if __name__ == "__main__":
    backup_plan = BackupPlan(
        config_path=Path("/home/duane/resticlvm/test/resticlvm_config.toml")
    )
    backup_plan.run_all_jobs()
