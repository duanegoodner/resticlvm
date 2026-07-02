"""Tests for the config_loader module."""

import tempfile
from pathlib import Path

import pytest

from resticlvm.orchestration.config_loader import load_config


def test_load_config_success():
    """Test loading a valid TOML configuration file."""
    toml_content = """
[prune_policy.standard]
keep_last = 10
keep_daily = 7
keep_weekly = 4
keep_monthly = 6
keep_yearly = 1

[volume.root]
volume_type = "lv_root"
vg_name = "vg0"
lv_name = "lv_root"
snapshot_size = "2G"
backup_source_path = "/"
exclude_paths = ["/dev", "/proc"]

[[volume.root.repositories]]
repo_path = "/srv/backup/test"
password_file = "/tmp/password.txt"
prune_policy = "standard"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = Path(f.name)

    try:
        config = load_config(temp_path)
        assert isinstance(config, dict)
        assert "volume" in config
        assert "root" in config["volume"]
        assert config["volume"]["root"]["vg_name"] == "vg0"
        assert config["volume"]["root"]["snapshot_size"] == "2G"
        assert config["volume"]["root"]["exclude_paths"] == ["/dev", "/proc"]
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
[prune_policy.light]
keep_last = 5
keep_daily = 7
keep_weekly = 4
keep_monthly = 6
keep_yearly = 1

[volume.boot]
volume_type = "standard_path"
backup_source_path = "/boot"
exclude_paths = []

[[volume.boot.repositories]]
repo_path = "/backup/boot"
password_file = "/tmp/pass.txt"
prune_policy = "light"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = f.name

    try:
        config = load_config(temp_path)
        assert isinstance(config, dict)
        assert "volume" in config
    finally:
        Path(temp_path).unlink()
