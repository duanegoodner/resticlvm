import subprocess
from pathlib import Path
from resticlvm.config_loader import load_config


def backup_standard_path(config: dict):
    cmd = [
        "./src/backup_path.sh",
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

    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    config_path = Path("/home/duane/resticlvm/test/resticlvm_config.toml")
    config = load_config(config_path)

    backup_boot_config = config["standard_path"]["boot"]
    backup_standard_path(config=backup_boot_config)
