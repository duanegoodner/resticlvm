#!/bin/bash

# Provides functions to create, mount, and clean up LVM snapshots
# for use in ResticLVM backups.
#
# Usage:
#   Intended to be sourced by backup scripts within the ResticLVM tool.
#
# Requirements:
#   - Must be run with root privileges (direct root or via sudo).
#   - LVM tools must be installed and available (lvcreate, lvremove, etc.).
#
# Exit codes:
#   Non-zero if any snapshot operation fails (unless in dry-run mode).

# Create an LVM snapshot for a given logical volume.
create_snapshot() {
    echo "📸 Creating LVM snapshot..."
    local dry_run=$1
    local snapshot_size=$2
    local snap_name=$3
    local vg_name=$4
    local lv_name=$5

    run_or_echo "$dry_run" "lvcreate --size $snapshot_size --snapshot --name $snap_name /dev/$vg_name/$lv_name"
}

# Mount an LVM snapshot read-only at a given mount point.
mount_snapshot() {
    local dry_run=$1
    local snapshot_mount_point=$2
    local vg_name=$3
    local snap_name=$4

    echo "📂 Mounting snapshot read-only..."
    run_or_echo "$dry_run" "mkdir -p \"$snapshot_mount_point\""
    run_or_echo "$dry_run" "mount /dev/$vg_name/$snap_name \"$snapshot_mount_point\" || { echo '❌ Failed to mount snapshot'; exit 1; }"
}

# Unmount and remove an LVM snapshot and its mount point.
clean_up_snapshot() {
    local dry_run="$1"
    local snapshot_mount_point="$2"
    local vg_name="$3"
    local snap_name="$4"

    echo "🧹 Cleaning up..."
    run_or_echo "$dry_run" "umount \"$snapshot_mount_point\""
    run_or_echo "$dry_run" "lvremove -y \"/dev/$vg_name/$snap_name\""
    run_or_echo "$dry_run" "rmdir \"$snapshot_mount_point\""
}

# Generate a timestamped name for an LVM snapshot.
generate_snapshot_name() {
    local vg_name="$1"
    local lv_name="$2"
    local timestamp
    timestamp=$(date +"%Y%m%d_%H%M%S")
    echo "${vg_name}_${lv_name}_snapshot_${timestamp}"
}

# Generate timestamped base directory for snapshot mounts
generate_mount_base() {
    local timestamp
    timestamp=$(date +"%Y%m%d_%H%M%S")
    echo "/tmp/resticlvm-${timestamp}"
}
