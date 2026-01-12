"""Tests for the dispatch module."""

from resticlvm.orchestration.dispatch import (
    LOGICAL_VOLUME_TOKEN_KEY_MAP,
    RESOURCE_DISPATCH,
    STANDARD_PATH_TOKEN_KEY_MAP,
)


def test_standard_path_token_key_map():
    """Test STANDARD_PATH_TOKEN_KEY_MAP has expected mappings."""
    assert STANDARD_PATH_TOKEN_KEY_MAP["-r"] == "restic_repo"
    assert STANDARD_PATH_TOKEN_KEY_MAP["-p"] == "restic_password_file"
    assert STANDARD_PATH_TOKEN_KEY_MAP["-s"] == "backup_source_path"
    assert STANDARD_PATH_TOKEN_KEY_MAP["-e"] == "exclude_paths"


def test_logical_volume_token_key_map():
    """Test LOGICAL_VOLUME_TOKEN_KEY_MAP has expected mappings."""
    assert LOGICAL_VOLUME_TOKEN_KEY_MAP["-g"] == "vg_name"
    assert LOGICAL_VOLUME_TOKEN_KEY_MAP["-l"] == "lv_name"
    assert LOGICAL_VOLUME_TOKEN_KEY_MAP["-z"] == "snapshot_size"
    assert LOGICAL_VOLUME_TOKEN_KEY_MAP["-r"] == "restic_repo"
    assert LOGICAL_VOLUME_TOKEN_KEY_MAP["-p"] == "restic_password_file"
    assert LOGICAL_VOLUME_TOKEN_KEY_MAP["-s"] == "backup_source_path"
    assert LOGICAL_VOLUME_TOKEN_KEY_MAP["-e"] == "exclude_paths"


def test_resource_dispatch_structure():
    """Test RESOURCE_DISPATCH has expected structure."""
    assert "standard_path" in RESOURCE_DISPATCH
    assert "logical_volume_root" in RESOURCE_DISPATCH
    assert "logical_volume_nonroot" in RESOURCE_DISPATCH


def test_resource_dispatch_standard_path():
    """Test RESOURCE_DISPATCH standard_path configuration."""
    standard_path = RESOURCE_DISPATCH["standard_path"]
    assert standard_path["script_name"] == "backup_path.sh"
    assert standard_path["token_key_map"] == STANDARD_PATH_TOKEN_KEY_MAP


def test_resource_dispatch_logical_volume_root():
    """Test RESOURCE_DISPATCH logical_volume_root configuration."""
    lv_root = RESOURCE_DISPATCH["logical_volume_root"]
    assert lv_root["script_name"] == "backup_lv_root.sh"
    assert lv_root["token_key_map"] == LOGICAL_VOLUME_TOKEN_KEY_MAP


def test_resource_dispatch_logical_volume_nonroot():
    """Test RESOURCE_DISPATCH logical_volume_nonroot configuration."""
    lv_nonroot = RESOURCE_DISPATCH["logical_volume_nonroot"]
    assert lv_nonroot["script_name"] == "backup_lv_nonroot.sh"
    assert lv_nonroot["token_key_map"] == LOGICAL_VOLUME_TOKEN_KEY_MAP


def test_resource_dispatch_keys_count():
    """Test that RESOURCE_DISPATCH has exactly the expected categories."""
    assert len(RESOURCE_DISPATCH) == 3
    expected_keys = {"standard_path", "logical_volume_root", "logical_volume_nonroot"}
    assert set(RESOURCE_DISPATCH.keys()) == expected_keys
