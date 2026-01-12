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

# Check if a repository path is a remote URL (not a local filesystem path)
is_remote_repo() {
    local repo="$1"
    # Remote repos start with protocol: sftp:, b2:, s3:, rest:, rclone:, azure:, gs:, swift:
    if [[ "$repo" =~ ^(sftp|b2|s3|rest|rclone|azure|gs|swift): ]]; then
        return 0  # true - it's remote
    else
        return 1  # false - it's local
    fi
}

# Remount a device as read-only.
remount_as_read_only() {
    local dry_run="$1"
    local backup_source="$2"

    if mountpoint -q "$backup_source"; then
        local dev target_mount
        dev=$(findmnt -n -o SOURCE --target "$backup_source")
        target_mount=$(findmnt -n -o TARGET --target "$backup_source")
        
        # Safety check: Never allow remounting root filesystem
        if [ "$target_mount" = "/" ]; then
            echo "❌ ERROR: Cannot remount root filesystem (/) as read-only"
            echo "   Backup source: $backup_source"
            echo "   Mount point: $target_mount"
            echo "   Device: $dev"
            echo ""
            echo "   → Set 'remount_readonly = false' in your configuration."
            echo "   → Consider using 'logical_volume_root' type for root filesystem backups."
            exit 1
        fi
        
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
# For remote repositories (sftp:, b2:, etc.), skips bind mount - they'll be used directly.
bind_repo_to_mounted_snapshot() {
    local dry_run="$1"
    local snapshot_mount_point="$2"
    local restic_repo="$3"
    local chroot_repo_full="$4"

    # Check if this is a remote repo
    if is_remote_repo "$restic_repo"; then
        echo "🌐 Remote repository detected: $restic_repo"
        echo "   Skipping bind mount (will use URL directly)"
        return 0
    fi

    # Local repo - do bind mount
    echo "🪝 Binding local Restic repo into chroot..."
    echo "  Snapshot mount point: $snapshot_mount_point"
    echo "  Restic repo: $restic_repo"
    echo "  Chroot repo path: $chroot_repo_full"
    run_or_echo "$dry_run" "mkdir -p $snapshot_mount_point/$chroot_repo_full"
    run_or_echo "$dry_run" "mount --bind $restic_repo $snapshot_mount_point/$chroot_repo_full"
}

# Bind /dev, /proc, and /sys into the snapshot to enable minimal chroot.
# Also bind SSH agent socket directory if it exists (needed for SFTP repos).
bind_chroot_essentials_to_mounted_snapshot() {
    local dry_run="$1"
    local snapshot_mount_point="$2"

    echo "🔧 Preparing chroot environment..."
    for path in /dev /proc /sys; do
        run_or_echo "$dry_run" "mount --bind $path $snapshot_mount_point$path"
    done
    
    # Bind /etc/resolv.conf for DNS resolution (needed for remote repos like B2/S3)
    if [ -f /etc/resolv.conf ]; then
        echo "🌐 Binding /etc/resolv.conf for DNS resolution..."
        run_or_echo "$dry_run" "mount --bind /etc/resolv.conf $snapshot_mount_point/etc/resolv.conf"
    fi
    
    # Bind SSH agent socket directory if it exists (for remote SFTP repos)
    if [ -n "$SSH_AUTH_SOCK" ] && [ -S "$SSH_AUTH_SOCK" ]; then
        echo "🔑 Binding SSH agent socket for remote repos..."
        local socket_dir=$(dirname "$SSH_AUTH_SOCK")
        local chroot_socket_dir="$snapshot_mount_point$socket_dir"
        
        # Create the directory in chroot if it doesn't exist
        run_or_echo "$dry_run" "mkdir -p \"$chroot_socket_dir\""
        
        # Bind mount the socket directory only if not already mounted
        if ! mountpoint -q "$chroot_socket_dir" 2>/dev/null; then
            run_or_echo "$dry_run" "mount --bind \"$socket_dir\" \"$chroot_socket_dir\""
        fi
    fi
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
# For remote repos, nothing to unmount.
unmount_repo_binding() {
    local dry_run="$1"
    local snapshot_mount_point="$2"
    local chroot_repo_full="$3"
    local restic_repo="$4"  # Optional: original repo path to check if remote

    # If we have the original repo path, check if it's remote
    if [ -n "$restic_repo" ] && is_remote_repo "$restic_repo"; then
        # Remote repo - nothing was bound, nothing to unmount
        return 0
    fi

    # Local repo - unmount it
    run_or_echo "$dry_run" "umount \"$snapshot_mount_point/$chroot_repo_full\""
}

# Unmount only the chroot essentials (/dev, /proc, /sys, resolv.conf, and SSH socket if bound)
# Unmount in reverse order: SSH socket first, resolv.conf, then /sys, /proc, /dev
unmount_chroot_essentials() {
    local dry_run="$1"
    local snapshot_mount_point="$2"

    # Unmount SSH agent socket directory first if it was bound
    if [ -n "$SSH_AUTH_SOCK" ]; then
        local socket_dir=$(dirname "$SSH_AUTH_SOCK")
        if mountpoint -q "$snapshot_mount_point$socket_dir" 2>/dev/null; then
            run_or_echo "$dry_run" "umount \"$snapshot_mount_point$socket_dir\""
        fi
    fi
    
    # Unmount /etc/resolv.conf if it was bound
    if mountpoint -q "$snapshot_mount_point/etc/resolv.conf" 2>/dev/null; then
        run_or_echo "$dry_run" "umount \"$snapshot_mount_point/etc/resolv.conf\""
    fi
    
    # Then unmount /sys, /proc, /dev in reverse order
    for path in /sys /proc /dev; do
        run_or_echo "$dry_run" "umount \"$snapshot_mount_point$path\""
    done
}
