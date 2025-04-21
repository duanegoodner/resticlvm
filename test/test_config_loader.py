from resticlvm.config_loader import load_config
from pathlib import Path
import pytest


@pytest.fixture
def expected_config():
    return {
        "path_sources": {
            "boot": {
                "source": "/boot",
                "repo_path": "/path/to/bootrepo/",
                "repo_password_file": "/path/to/boot/repo/password_file",
                "excldue_paths": [],
                "remount_readonly": True,
            }
        },
        "logical_volume_sources": {
            "example_lvm": {
                "source_vg_name": "vg_example",
                "source_lv_name": "lv_example",
                "snapshot_mount_point": "/path/to/snapshot/dir/",
                "snapshot_size": 1,
                "snapshot_size_unit": "G",
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
        result["path_sources"] == expected_config["path_sources"]
    ), f"Expected {expected_config['partitions']}, but got {result['partitions']}"

    assert (
        result["logical_volume_sources"]
        == expected_config["logical_volume_sources"]
    ), f"Expected {expected_config['logical_volumes']}, but got {result['logical_volumes']}"
