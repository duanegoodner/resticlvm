STANDARD_PATH_TOKEN_KEY_MAP = {
    "-r": "restic_repo",
    "-p": "restic_password_file",
    "-s": "backup_source_path",
    "-e": "exclude_paths",
    "-m": "remount_readonly",
}

LOGICAL_VOLUME_TOKEN_KEY_MAP = {
    "-g": "vg_name",
    "-l": "lv_name",
    "-z": "snapshot_size",
    "-r": "restic_repo",
    "-p": "restic_password_file",
    "-s": "backup_source_path",
    "-e": "exclude_paths",
}

RESOURCE_DISPATCH = {
    "standard_path": {
        "script_name": "backup_path.sh",
        "token_key_map": STANDARD_PATH_TOKEN_KEY_MAP,
    },
    "logical_volume_root": {
        "script_name": "backup_lv_root.sh",
        "token_key_map": LOGICAL_VOLUME_TOKEN_KEY_MAP,
    },
    "logical_volume_nonroot": {
        "script_name": "backup_lv_nonroot.sh",
        "token_key_map": LOGICAL_VOLUME_TOKEN_KEY_MAP,
    },
}
