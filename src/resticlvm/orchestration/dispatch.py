"""dispatch.py

Defines token-to-config key mappings and script dispatch tables
for ResticLVM backup jobs.
"""

from resticlvm.orchestration.backup_config import VolumeType

# Mapping of CLI tokens to configuration keys for standard path backups.
STANDARD_PATH_TOKEN_KEY_MAP = {
    "-s": "backup_source_path",
    "-e": "exclude_paths",
}

# Mapping of CLI tokens to configuration keys for logical volume backups.
LOGICAL_VOLUME_TOKEN_KEY_MAP = {
    "-g": "vg_name",
    "-l": "lv_name",
    "-z": "snapshot_size",
    "-s": "backup_source_path",
    "-e": "exclude_paths",
}

# Dispatch table mapping volume types to their corresponding
# script names and token-key mappings.
RESOURCE_DISPATCH = {
    VolumeType.STANDARD_PATH: {
        "script_name": "backup_path.sh",
        "token_key_map": STANDARD_PATH_TOKEN_KEY_MAP,
    },
    VolumeType.LV_ROOT: {
        "script_name": "backup_lv_root.sh",
        "token_key_map": LOGICAL_VOLUME_TOKEN_KEY_MAP,
    },
    VolumeType.LV_NONROOT: {
        "script_name": "backup_lv_nonroot.sh",
        "token_key_map": LOGICAL_VOLUME_TOKEN_KEY_MAP,
    },
}
