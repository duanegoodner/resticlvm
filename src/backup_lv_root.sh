#!/bin/bash

set -euo pipefail

# shellcheck disable=SC1091
source "$(dirname "$0")/backup_helpers.sh"

# ─── Require Running as Root ─────────────────────────────────────
root_check

# ─── Default Values ──────────────────────────────────────────────
VG_NAME=""
LV_NAME=""
SNAP_SIZE=""
RESTIC_REPO=""
RESTIC_PASSWORD_FILE=""
BACKUP_SOURCE="/" # Inside chroot
EXCLUDE_PATHS="/dev /media /mnt /proc /run /sys /tmp /var/tmp /var/lib/libvirt/images"
DRY_RUN=false

CHROOT_REPO_PATH="/.restic_repo"

# ─── Parse and Validate Arguments ─────────────────────────────────
parse_for_lv usage_lv_root "$@"
validate_args usage_lv_root VG_NAME LV_NAME SNAP_SIZE RESTIC_REPO RESTIC_PASSWORD_FILE

# ─── Derived Variables ───────────────────────────────────────────
SNAP_NAME=$(generate_snapshot_name "$VG_NAME" "$LV_NAME")
LV_DEVICE_PATH="/dev/$VG_NAME/$LV_NAME"
SNAPSHOT_MOUNT_POINT="/srv/${SNAP_NAME}"

# ─── Pre-checks ───────────────────────────────────────────────────
check_device_path "$LV_DEVICE_PATH"
LV_MOUNT_POINT=$(check_mount_point "$LV_DEVICE_PATH")
confirm_source_in_lv "$LV_MOUNT_POINT" "$BACKUP_SOURCE"
confirm_not_yet_exist_snapshot_mount_point "$SNAPSHOT_MOUNT_POINT"

# ─── Display Configuration ───────────────────────────────────────
display_config_lvm
display_dry_run_message "$DRY_RUN"

# ─── Create Snapshot and Mount ────────────────────────────────────
create_snapshot "$DRY_RUN" "$SNAP_SIZE" "$SNAP_NAME" "$VG_NAME" "$LV_NAME"
mount_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"

# ─── Prepare Chroot Environment ───────────────────────────────────
CHROOT_REPO_FULL="$CHROOT_REPO_PATH/$(basename "$RESTIC_REPO")"

bind_repo_to_mounted_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$RESTIC_REPO" "$CHROOT_REPO_FULL"
bind_chroot_essentials_to_mounted_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT"

# ─── Build Restic Backup Command ──────────────────────────────────
EXCLUDE_PATHS="$CHROOT_REPO_PATH $EXCLUDE_PATHS"

EXCLUDE_ARGS=()
populate_exclude_paths EXCLUDE_ARGS "$EXCLUDE_PATHS"

RESTIC_TAGS=()
populate_restic_tags RESTIC_TAGS "$EXCLUDE_PATHS"

RESTIC_CMD="export RESTIC_PASSWORD_FILE=$RESTIC_PASSWORD_FILE && restic"
RESTIC_CMD+=" ${EXCLUDE_ARGS[*]}"
RESTIC_CMD+=" ${RESTIC_TAGS[*]}"
RESTIC_CMD+=" -r $CHROOT_REPO_FULL"
RESTIC_CMD+=" backup $BACKUP_SOURCE"
RESTIC_CMD+=" --verbose"

# ─── Execute Backup ───────────────────────────────────────────────
echo "🚀 Running Restic backup in chroot..."
run_in_chroot_or_echo "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$RESTIC_CMD"

# ─── Cleanup ──────────────────────────────────────────────────────
unmount_chroot_bindings "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$CHROOT_REPO_FULL"
clean_up_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"

echo "✅ Backup completed (or would have, in dry-run mode)."
