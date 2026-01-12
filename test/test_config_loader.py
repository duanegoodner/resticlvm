"""Tests for the config_loader module."""

import tempfile
from pathlib import Path

import pytest

from resticlvm.orchestration.config_loader import load_config


def test_load_config_success():
    """Test loading a valid TOML configuration file."""
    toml_content = """
[logical_volume_root.root]
vg_name = "vg0"
lv_name = "lv_root"
snapshot_size = "2G"
restic_repo = "/srv/backup/test"
restic_password_file = "/tmp/password.txt"
backup_source_path = "/"
exclude_paths = ["/dev", "/proc"]
prune_keep_last = 10
prune_keep_daily = 7
prune_keep_weekly = 4
prune_keep_monthly = 6
prune_keep_yearly = 1
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = Path(f.name)

    try:
        config = load_config(temp_path)
        assert isinstance(config, dict)
        assert "logical_volume_root" in config
        assert "root" in config["logical_volume_root"]
        assert config["logical_volume_root"]["root"]["vg_name"] == "vg0"
        assert config["logical_volume_root"]["root"]["snapshot_size"] == "2G"
        assert config["logical_volume_root"]["root"]["exclude_paths"] == ["/dev", "/proc"]
    finally:
        temp_path.unlink()


def test_load_config_file_not_found():
    """Test that FileNotFoundError is raised for non-existent file."""
    with pytest.raises(FileNotFoundError):
        load_config("/non/existent/path.toml")


def test_load_config_invalid_toml():
    """Test that TOMLDecodeError is raised for invalid TOML syntax."""
    import tomllib
    
    invalid_toml = """
[section
invalid syntax here
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(invalid_toml)
        temp_path = Path(f.name)

    try:
        with pytest.raises(tomllib.TOMLDecodeError):
            load_config(temp_path)
    finally:
        temp_path.unlink()


def test_load_config_with_path_string():
    """Test loading config with a string path instead of Path object."""
    toml_content = """
[standard_path.boot]
backup_source_path = "/boot"
restic_repo = "/backup/boot"
restic_password_file = "/tmp/pass.txt"
exclude_paths = []

prune_keep_last = 5
prune_keep_daily = 7
prune_keep_weekly = 4
prune_keep_monthly = 6
prune_keep_yearly = 1
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = f.name

    try:
        config = load_config(temp_path)  # Pass as string, not Path
        assert isinstance(config, dict)
        assert "standard_path" in config
    finally:
        Path(temp_path).unlink()
