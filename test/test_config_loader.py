from resticlvm.config_loader import load_config
from pathlib import Path
import pytest


@pytest.fixture
def expected_config():
    return {
        "general": {"dry_run": True},
        "partitions": {
            "boot": {
                "mount_point": "/boot",
                "repo_path": "/path/to/bootrepo/",
                "repo_password_file": "/path/to/boot/repo/password_file",
                "excldue_paths": [],
            }
        },
        "logical_volumes": {
            "example_lvm": {
                "vg_name": "vg_example",
                "lv_name": "lv_example",
                "snapshot_mount_point": "/path/to/snapshot/dir/",
                "repo_path": "/path/to/example_lvm/repo/",
                "paths_for_backup": ["/"],
                "exclude_paths": [
                    "/dev",
                    "/media",
                    "/mnt",
                    "/proc",
                    "/run",
                    "/sys",
                    "/tmp",
                    "/var/tmp",
                    "/var/lib/libvirt/images",
                    "/var/lib/libvirt/isos",
                ],
                "snapshot_size": "10G",
            }
        },
    }


def test_load_config_str(expected_config):
    this_dir = Path(__file__).parent
    config_path = this_dir / "example_config.toml"
    result = load_config(config_path)

    assert (
        result.keys() == expected_config.keys()
    ), f"Expected keys {expected_config.keys()}, but got {result.keys()}"

    assert (
        result["general"] == expected_config["general"]
    ), f"Expected {expected_config['general']}, but got {result['general']}"

    assert (
        result["partitions"] == expected_config["partitions"]
    ), f"Expected {expected_config['partitions']}, but got {result['partitions']}"
    assert (
        result["logical_volumes"] == expected_config["logical_volumes"]
    ), f"Expected {expected_config['logical_volumes']}, but got {result['logical_volumes']}"
