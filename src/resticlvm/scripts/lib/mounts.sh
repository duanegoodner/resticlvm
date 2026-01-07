#!/bin/bash

# Provides functions for remounting volumes, binding Restic repositories,
# and setting up minimal chroot environments for backup operations.
#
# Usage:
#   Intended to be sourced by backup scripts within the ResticLVM tool.
#
# Requirements:
#   - Must be run with root privileges (direct root or via sudo).
#   - mount, findmnt utilities must be available in PATH.
#
# Exit codes:
#   Non-zero if remounts or bind-mounts fail (unless in dry-run mode).

# Remount a device as read-only.
remount_as_read_only() {
    local dry_run="$1"
    local backup_source="$2"

    if mountpoint -q "$backup_source"; then
        local dev
        dev=$(findmnt -n -o SOURCE --target "$backup_source")
        echo "🔒 Remounting $dev as read-only..."
        run_or_echo "$dry_run" "mount -o remount,ro $dev"
    else
        echo "⚠️ $backup_source is not a mount point. Cannot use remount-as-ro option."
        exit 1
    fi
}

# Remount a device as read-write.
remount_as_read_write() {
    local dry_run="$1"
    local backup_source="$2"

    if mountpoint -q "$backup_source"; then
        local dev
        dev=$(findmnt -n -o SOURCE --target "$backup_source")
        echo "🔓 Remounting $dev as read-write..."
        run_or_echo "$dry_run" "mount -o remount,rw $dev"
    else
        echo "⚠️ $backup_source is not a mount point. Cannot remount as read-write."
        exit 1
    fi
}

# Bind-mount the Restic repository into the snapshot for chroot backup.
bind_repo_to_mounted_snapshot() {
    local dry_run="$1"
    local snapshot_mount_point="$2"
    local restic_repo="$3"
    local chroot_repo_full="$4"

    echo "🪝 Binding Restic repo into chroot..."
    echo "  Snapshot mount point: $snapshot_mount_point"
    echo "  Restic repo: $restic_repo"
    echo "  Chroot repo path: $chroot_repo_full"
    run_or_echo "$dry_run" "mkdir -p $snapshot_mount_point/$chroot_repo_full"
    run_or_echo "$dry_run" "mount --bind $restic_repo $snapshot_mount_point/$chroot_repo_full"
}

# Bind /dev, /proc, and /sys into the snapshot to enable minimal chroot.
bind_chroot_essentials_to_mounted_snapshot() {
    local dry_run="$1"
    local snapshot_mount_point="$2"

    echo "🔧 Preparing chroot environment..."
    for path in /dev /proc /sys; do
        run_or_echo "$dry_run" "mount --bind $path $snapshot_mount_point$path"
    done
}

# Unmount Restic repo and chroot essentials from the snapshot.
unmount_chroot_bindings() {
    local dry_run="$1"
    local snapshot_mount_point="$2"
    local chroot_repo_full="$3"

    run_or_echo "$dry_run" "umount \"$snapshot_mount_point/$chroot_repo_full\""
    for path in /dev /proc /sys; do
        run_or_echo "$dry_run" "umount \"$snapshot_mount_point$path\""
    done
}

# Unmount just the repo binding (for use in multi-repo loops)
unmount_repo_binding() {
    local dry_run="$1"
    local snapshot_mount_point="$2"
    local chroot_repo_full="$3"

    run_or_echo "$dry_run" "umount \"$snapshot_mount_point/$chroot_repo_full\""
}

# Unmount only the chroot essentials (/dev, /proc, /sys)
unmount_chroot_essentials() {
    local dry_run="$1"
    local snapshot_mount_point="$2"

    for path in /dev /proc /sys; do
        run_or_echo "$dry_run" "umount \"$snapshot_mount_point$path\""
    done
}
