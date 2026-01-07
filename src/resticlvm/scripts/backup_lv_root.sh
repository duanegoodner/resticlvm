#!/bin/bash

# Backup a logical volume that is mounted at the system root ("/") using
# Restic and LVM snapshots. Runs the backup inside a chroot environment
# created from the mounted snapshot.
#
# Arguments:
#   -g  Volume group name.
#   -l  Logical volume name.
#   -z  Snapshot size (e.g., "5G").
#   -r  Path to the Restic repository.
#   -p  Path to the Restic password file.
#   -s  (Optional) Path to backup source inside LV (default: "/").
#   -e  (Optional) Comma-separated list of paths to exclude.
#   --dry-run  (Optional) Show actions without executing them.
#
# Usage:
#   This script is intended to be called internally by the ResticLVM tool.
#
# Requirements:
#   - Must be run with root privileges (direct root or via sudo).
#   - Restic must be installed and available in PATH.
#   - LVM must be installed and functional.
#
# Exit codes:
#   0  Success
#   1  Any fatal error

set -euo pipefail

# shellcheck disable=SC1091
source "$(dirname "$0")/backup_helpers.sh"

# ─── Require Running as Root ─────────────────────────────────────
root_check

# ─── Default Values ──────────────────────────────────────────────
VG_NAME=""
LV_NAME=""
SNAPSHOT_SIZE=""
RESTIC_REPOS=()
RESTIC_PASSWORD_FILES=()
BACKUP_SOURCE_PATH="/" # Inside chroot
EXCLUDE_PATHS="/dev /media /mnt /proc /run /sys /tmp /var/tmp /var/lib/libvirt/images"
DRY_RUN=false

CHROOT_REPO_PATH="/.restic_repo"

# ─── Parse and Validate Arguments ─────────────────────────────────
parse_for_lv usage_lv_root "$@"

# Validate basic LVM args
validate_args usage_lv_root VG_NAME LV_NAME SNAPSHOT_SIZE

# Validate repository arrays
if [ ${#RESTIC_REPOS[@]} -eq 0 ]; then
    echo "❌ Error: At least one --restic-repo is required"
    usage_lv_root
fi

if [ ${#RESTIC_REPOS[@]} -ne ${#RESTIC_PASSWORD_FILES[@]} ]; then
    echo "❌ Error: Number of repos (${#RESTIC_REPOS[@]}) must match number of password files (${#RESTIC_PASSWORD_FILES[@]})"
    usage_lv_root
fi

# ─── Derived Variables ───────────────────────────────────────────
SNAP_NAME=$(generate_snapshot_name "$VG_NAME" "$LV_NAME")
LV_DEVICE_PATH="/dev/$VG_NAME/$LV_NAME"
SNAPSHOT_MOUNT_POINT="/srv/${SNAP_NAME}"

# ─── Pre-checks ───────────────────────────────────────────────────
check_device_path "$LV_DEVICE_PATH"
LV_MOUNT_POINT=$(check_mount_point "$LV_DEVICE_PATH")
confirm_source_in_lv "$LV_MOUNT_POINT" "$BACKUP_SOURCE_PATH"
confirm_not_yet_exist_snapshot_mount_point "$SNAPSHOT_MOUNT_POINT"

# ─── Display Configuration ───────────────────────────────────────
display_config "LVM Snapshot Backup Configuration" \
    VG_NAME LV_NAME SNAPSHOT_SIZE SNAP_NAME SNAPSHOT_MOUNT_POINT \
    EXCLUDE_PATHS BACKUP_SOURCE_PATH DRY_RUN

echo "Repositories: ${#RESTIC_REPOS[@]}"
for i in "${!RESTIC_REPOS[@]}"; do
    echo "  $((i+1)). ${RESTIC_REPOS[$i]}"
done

display_dry_run_message "$DRY_RUN"

# ─── Create Snapshot and Mount ────────────────────────────────────
create_snapshot "$DRY_RUN" "$SNAPSHOT_SIZE" "$SNAP_NAME" "$VG_NAME" "$LV_NAME"
mount_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"

# ─── Prepare Chroot Environment ───────────────────────────────────
bind_chroot_essentials_to_mounted_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT"

# ─── Build Exclude Arguments (Once) ───────────────────────────────
EXCLUDE_PATHS="$CHROOT_REPO_PATH $EXCLUDE_PATHS"

EXCLUDE_ARGS=()
populate_exclude_paths EXCLUDE_ARGS "$EXCLUDE_PATHS"

RESTIC_TAGS=()
populate_restic_tags RESTIC_TAGS "$EXCLUDE_PATHS"

# ─── Loop Over Repositories ───────────────────────────────────────
echo "🚀 Backing up to ${#RESTIC_REPOS[@]} repository(ies)..."

for i in "${!RESTIC_REPOS[@]}"; do
    RESTIC_REPO="${RESTIC_REPOS[$i]}"
    RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILES[$i]}"
    
    echo ""
    echo "▶️  Repository $((i+1))/${#RESTIC_REPOS[@]}: $RESTIC_REPO"
    
    # Bind this repo to chroot (skip for remote repos)
    CHROOT_REPO_FULL="$CHROOT_REPO_PATH/$(basename "$RESTIC_REPO")"
    bind_repo_to_mounted_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$RESTIC_REPO" "$CHROOT_REPO_FULL"
    
    # Determine which repo path to use in restic command
    if is_remote_repo "$RESTIC_REPO"; then
        # Remote repo - use the URL directly
        EFFECTIVE_REPO="$RESTIC_REPO"
    else
        # Local repo - use the chroot-bound path
        EFFECTIVE_REPO="$CHROOT_REPO_FULL"
    fi
    
    # Build Restic command for this repo
    RESTIC_CMD="export RESTIC_PASSWORD_FILE=$RESTIC_PASSWORD_FILE && restic"
    RESTIC_CMD+=" ${EXCLUDE_ARGS[*]}"
    RESTIC_CMD+=" ${RESTIC_TAGS[*]}"
    RESTIC_CMD+=" -r $EFFECTIVE_REPO"
    RESTIC_CMD+=" backup $BACKUP_SOURCE_PATH"
    RESTIC_CMD+=" --verbose"
    
    # Execute backup for this repo
    run_in_chroot_or_echo "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$RESTIC_CMD"
    
    # Unbind just this repo from chroot (keep /dev, /proc, /sys for next repo)
    unmount_repo_binding "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$CHROOT_REPO_FULL" "$RESTIC_REPO"
done

# ─── Cleanup ──────────────────────────────────────────────────────
# Unmount chroot essentials once after all repos are done
unmount_chroot_essentials "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT"
clean_up_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"

echo ""
echo "✅ Backup completed for ${#RESTIC_REPOS[@]} repository(ies) (or would have, in dry-run mode)."
