import subprocess
import importlib.resources as pkg_resources
import sys
from pathlib import Path

from resticlvm.config_loader import load_config
from resticlvm import scripts


def backup_standard_path(config: dict):
    try:
        args_list = [
            "-r",
            config["restic_repo"],
            "-p",
            config["restic_password_file"],
            "-s",
            config["backup_source_path"],
            "-e",
            "".join(config["exclude_paths"]),
            "-m",
            str(config["remount_readonly"]).lower(),
        ]
    except KeyError as e:
        print(f"Missing key in config: {e}")
        return
    except TypeError as e:
        print(f"Invalid type in config: {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return

    script_path = pkg_resources.files(scripts) / "backup_path.sh"

    cmd = ["bash", str(script_path)] + args_list

    try:
        subprocess.run(
            args=cmd, check=True, stdout=sys.stdout, stderr=sys.stderr
        )
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        return
    except FileNotFoundError as e:
        print(f"Script not found: {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return


if __name__ == "__main__":
    config_path = Path("/home/duane/resticlvm/test/resticlvm_config.toml")
    config = load_config(config_path)

    backup_boot_config = config["standard_path"]["boot"]
    backup_standard_path(config=backup_boot_config)
