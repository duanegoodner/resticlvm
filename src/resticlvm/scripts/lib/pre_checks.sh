#!/bin/bash

# Provides validation and pre-check functions to ensure the environment
# is ready for safe ResticLVM backup operations.
#
# Usage:
#   Intended to be sourced by backup scripts within the ResticLVM tool.
#
# Requirements:
#   - Must be run with root privileges (direct root or via sudo).
#   - findmnt, realpath utilities must be available in PATH.
#
# Exit codes:
#   Non-zero if validation or pre-conditions fail.

# Verify that the script is running with root privileges.
root_check() {
    if [ "$EUID" -ne 0 ]; then
        echo "❌ Please run as root or with sudo."
        exit 1
    fi
}

# Check if a given filesystem path exists.
check_if_path_exists() {
    local path="$1"
    if ! [ -e "$path" ]; then
        echo "❌ Path $path does not exist."
        exit 1
    fi
}

# Check if a logical volume device path exists.
check_device_path() {
    local device_path="$1"
    if ! [ -e "$device_path" ]; then
        echo "❌ Logical volume $device_path does not exist."
        exit 1
    fi
}

# Verify that a logical volume device is mounted and return its mount point.
check_mount_point() {
    local device_path="$1"
    local mount_point
    mount_point=$(findmnt -n -o TARGET --source "$device_path")

    if [ -n "$mount_point" ]; then
        echo "$mount_point" # Output only the mount point
    else
        echo "❌  LV $device_path is not currently mounted but must be mounted for backup."
        echo "   → Please mount it before running this script."
        echo "   → Example: mount $device_path /mnt."
        echo "   → Exiting."
        exit 1
    fi
}

# Confirm that the backup source path is inside the mounted LV.
confirm_source_in_lv() {
    local lv_mount_point="$1"
    local backup_source="$2"

    real_mount=$(realpath -m "$lv_mount_point")
    real_backup=$(realpath -m "$backup_source")
    echo "Resolved mount point: $real_mount"
    echo "Resolved backup source: $real_backup"

    if [[ "$real_backup" != "$real_mount"* ]]; then
        echo "❌ Error: Backup source '$backup_source' is not within logical volume mount point '$real_mount'"
        echo "   → Resolved path: $real_backup"
        exit 1
    elif [[ ! -e "$real_backup" ]]; then
        echo "❌ Error: Backup source path '$real_backup' does not exist."
        exit 1
    else
        echo "✅ Backup source $backup_source resolves to $real_backup and is valid."
    fi
}

# Ensure that the snapshot mount point does not already exist.
confirm_not_yet_exist_snapshot_mount_point() {
    local snapshot_mount_point="$1"

    if [[ -e "$snapshot_mount_point" ]]; then
        echo "❌ Mount point $snapshot_mount_point already exists. Aborting."
        exit 1
    fi
}
