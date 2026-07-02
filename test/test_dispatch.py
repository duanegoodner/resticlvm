"""Tests for the dispatch module."""

from resticlvm.orchestration.backup_config import VolumeType
from resticlvm.orchestration.dispatch import (
    LOGICAL_VOLUME_TOKEN_KEY_MAP,
    RESOURCE_DISPATCH,
    STANDARD_PATH_TOKEN_KEY_MAP,
)


def test_standard_path_token_key_map():
    """Test STANDARD_PATH_TOKEN_KEY_MAP has expected mappings."""
    assert STANDARD_PATH_TOKEN_KEY_MAP["-s"] == "backup_source_path"
    assert STANDARD_PATH_TOKEN_KEY_MAP["-e"] == "exclude_paths"


def test_logical_volume_token_key_map():
    """Test LOGICAL_VOLUME_TOKEN_KEY_MAP has expected mappings."""
    assert LOGICAL_VOLUME_TOKEN_KEY_MAP["-g"] == "vg_name"
    assert LOGICAL_VOLUME_TOKEN_KEY_MAP["-l"] == "lv_name"
    assert LOGICAL_VOLUME_TOKEN_KEY_MAP["-z"] == "snapshot_size"
    assert LOGICAL_VOLUME_TOKEN_KEY_MAP["-s"] == "backup_source_path"
    assert LOGICAL_VOLUME_TOKEN_KEY_MAP["-e"] == "exclude_paths"


def test_resource_dispatch_structure():
    """Test RESOURCE_DISPATCH has expected structure."""
    assert VolumeType.STANDARD_PATH in RESOURCE_DISPATCH
    assert VolumeType.LV_ROOT in RESOURCE_DISPATCH
    assert VolumeType.LV_NONROOT in RESOURCE_DISPATCH


def test_resource_dispatch_standard_path():
    """Test RESOURCE_DISPATCH standard_path configuration."""
    entry = RESOURCE_DISPATCH[VolumeType.STANDARD_PATH]
    assert entry["script_name"] == "backup_path.sh"
    assert entry["token_key_map"] == STANDARD_PATH_TOKEN_KEY_MAP


def test_resource_dispatch_lv_root():
    """Test RESOURCE_DISPATCH lv_root configuration."""
    entry = RESOURCE_DISPATCH[VolumeType.LV_ROOT]
    assert entry["script_name"] == "backup_lv_root.sh"
    assert entry["token_key_map"] == LOGICAL_VOLUME_TOKEN_KEY_MAP


def test_resource_dispatch_lv_nonroot():
    """Test RESOURCE_DISPATCH lv_nonroot configuration."""
    entry = RESOURCE_DISPATCH[VolumeType.LV_NONROOT]
    assert entry["script_name"] == "backup_lv_nonroot.sh"
    assert entry["token_key_map"] == LOGICAL_VOLUME_TOKEN_KEY_MAP


def test_resource_dispatch_keys_count():
    """Test that RESOURCE_DISPATCH has exactly the expected volume types."""
    assert len(RESOURCE_DISPATCH) == 3
    assert set(RESOURCE_DISPATCH.keys()) == set(VolumeType)
