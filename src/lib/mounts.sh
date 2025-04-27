#!/bin/bash

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

bind_chroot_essentials_to_mounted_snapshot() {
    local dry_run="$1"
    local snapshot_mount_point="$2"

    echo "🔧 Preparing chroot environment..."
    for path in /dev /proc /sys; do
        run_or_echo "$dry_run" "mount --bind $path $snapshot_mount_point$path"
    done
}

unmount_chroot_bindings() {
    local dry_run="$1"
    local snapshot_mount_point="$2"
    local chroot_repo_full="$3"

    run_or_echo "$dry_run" "umount \"$snapshot_mount_point/$chroot_repo_full\""
    for path in /dev /proc /sys; do
        run_or_echo "$dry_run" "umount \"$snapshot_mount_point$path\""
    done
}
