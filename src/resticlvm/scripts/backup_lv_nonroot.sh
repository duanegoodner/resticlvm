#!/bin/bash

# Backup a logical volume that is mounted somewhere other than "/" using
# Restic and LVM snapshots. Backs up directly from the mounted snapshot
# without using a chroot environment.
#
# Note:
#   - The path stored in the Restic repository will differ from the
#     original source path (e.g., backing up /data will store under /srv/data).
#
# Arguments:
#   -g  Volume group name.
#   -l  Logical volume name.
#   -z  Snapshot size (e.g., "5G").
#   -r  Path to the Restic repository.
#   -p  Path to the Restic password file.
#   -s  Path to backup source directory inside LV (e.g., "/data").
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
RESTIC_REPO=""
RESTIC_PASSWORD_FILE=""
BACKUP_SOURCE_PATH=""
EXCLUDE_PATHS=""
DRY_RUN=false

# ─── Parse and Validate Arguments ─────────────────────────────────
parse_arguments usage_lv_nonroot "vg-name lv-name snap-size restic-repo password-file backup-source exclude-paths dry-run" "$@"
validate_args usage_lv_nonroot VG_NAME LV_NAME SNAPSHOT_SIZE RESTIC_REPO RESTIC_PASSWORD_FILE

# ─── Derived Variables ───────────────────────────────────────────
SNAP_NAME=$(generate_snapshot_name "$VG_NAME" "$LV_NAME")
LV_DEVICE_PATH="/dev/$VG_NAME/$LV_NAME"

# ─── Pre-checks ───────────────────────────────────────────────────
check_device_path "$LV_DEVICE_PATH"
LV_MOUNT_POINT=$(check_mount_point "$LV_DEVICE_PATH")
confirm_source_in_lv "$LV_MOUNT_POINT" "$BACKUP_SOURCE_PATH"

# Mount point for snapshot
SNAPSHOT_MOUNT_POINT="/srv${LV_MOUNT_POINT}"

# Backup path inside the mounted snapshot
REL_PATH="${BACKUP_SOURCE_PATH#$LV_MOUNT_POINT}"
SNAPSHOT_BACKUP_PATH="$SNAPSHOT_MOUNT_POINT$REL_PATH"

confirm_not_yet_exist_snapshot_mount_point "$SNAPSHOT_MOUNT_POINT"

# ─── Display Configuration ───────────────────────────────────────
display_config "LVM Snapshot Backup Configuration" \
    VG_NAME LV_NAME SNAPSHOT_SIZE SNAP_NAME SNAPSHOT_MOUNT_POINT \
    RESTIC_REPO RESTIC_PASSWORD_FILE EXCLUDE_PATHS BACKUP_SOURCE_PATH DRY_RUN

display_dry_run_message "$DRY_RUN"

# ─── Create and Mount Snapshot ────────────────────────────────────
create_snapshot "$DRY_RUN" "$SNAPSHOT_SIZE" "$SNAP_NAME" "$VG_NAME" "$LV_NAME"
mount_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"

# ─── Build Restic Backup Command ──────────────────────────────────
EXCLUDE_ARGS=()
populate_exclude_paths_for_lv_nonroot EXCLUDE_ARGS "$EXCLUDE_PATHS" "$SNAPSHOT_MOUNT_POINT"

RESTIC_TAGS=()
populate_restic_tags_for_lv_nonroot RESTIC_TAGS "$EXCLUDE_PATHS" "$SNAPSHOT_MOUNT_POINT"

RESTIC_CMD="restic -r $RESTIC_REPO"
RESTIC_CMD+=" --password-file=$RESTIC_PASSWORD_FILE"
RESTIC_CMD+=" backup $SNAPSHOT_BACKUP_PATH"
RESTIC_CMD+=" ${EXCLUDE_ARGS[*]}"
RESTIC_CMD+=" ${RESTIC_TAGS[*]}"
RESTIC_CMD+=" --verbose"

# ─── Execute Backup ───────────────────────────────────────────────
echo "🚀 Running Restic backup..."
run_or_echo "$DRY_RUN" "$RESTIC_CMD"

# ─── Cleanup ──────────────────────────────────────────────────────
clean_up_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"

echo "✅ Backup completed (or would have, in dry-run mode)."
