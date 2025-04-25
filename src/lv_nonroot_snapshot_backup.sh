#!/bin/bash

set -euo pipefail

# shellcheck disable=SC1091
source "$(dirname "$0")/backup_helpers.sh"

root_check

# ─── Default values ───────────────────────────────────────────────

VG_NAME=""
LV_NAME=""
SNAP_SIZE=""
RESTIC_REPO=""
RESTIC_PASSWORD_FILE=""
BACKUP_SOURCE=""
EXCLUDE_PATHS=""
DRY_RUN=false
DRY_RUN_PREFIX="\033[1;33m[DRY RUN]\033[0m"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SNAP_NAME="${VG_NAME}_${LV_NAME}_snapshot_${TIMESTAMP}"
SNAPSHOT_MOUNT_POINT="/srv${SNAP_NAME}"

parse_arguments usage_lv_nonroot "$@"
validate_args usage_lv_nonroot
# Define LV_DEVICE_PATH now that VG_NAME and LV_NAME are set
LV_DEVICE_PATH="/dev/$VG_NAME/$LV_NAME"

# ─── Pre-check: does lhe logical volue exist  ──────
check_device_path "$LV_DEVICE_PATH"

# ─── Pre-check: is the LV mounted? ──────
# LV_MOUNT_POINT=$(findmnt -n -o TARGET --source "$LV_DEVICE_PATH")
LV_MOUNT_POINT=$(check_mount_point "$LV_DEVICE_PATH")

REAL_MOUNT=$(realpath "$LV_MOUNT_POINT")

# ─── Generate names based on timestamp ────────────────────────────

REAL_BACKUP=$(realpath -m "$BACKUP_SOURCE")

REL_PATH="${BACKUP_SOURCE#$LV_MOUNT_POINT}"
SNAPSHOT_BACKUP_PATH="$SNAPSHOT_MOUNT_POINT$REL_PATH"

# ─── Pre-check: does source path exist under logical volume mount point  ──────
# Resolve real paths

confirm_source_in_lv "$REAL_BACKUP" "$REAL_MOUNT" "$BACKUP_SOURCE"

confirm_not_yet_exist_snapshot_mount_point "$SNAPSHOT_MOUNT_POINT"

display_snapshot_backup_config

display_dry_run_message "$DRY_RUN"

echo "📸 Creating snapshot..."
run_or_echo "$DRY_RUN" "lvcreate --size \"$SNAP_SIZE\" --snapshot --name \"$SNAP_NAME\" \"/dev/$VG_NAME/$LV_NAME\""

echo "📂 Mounting snapshot..."
run_or_echo "$DRY_RUN" "mkdir -p \"$SNAPSHOT_MOUNT_POINT\""
run_or_echo "$DRY_RUN" "mount \"/dev/$VG_NAME/$SNAP_NAME\" \"$SNAPSHOT_MOUNT_POINT\""

# ─── Build and run Restic backup ─────────────────────────────────
echo "🚀 Running Restic backup..."
EXCLUDE_ARGS=()
RESTIC_TAGS=()
for path in $EXCLUDE_PATHS; do
    rel="${path#$LV_MOUNT_POINT}"
    abs="$SNAPSHOT_MOUNT_POINT$rel"
    EXCLUDE_ARGS+=("--exclude=$abs")
    tag_path="${rel#/}" # Remove leading slash for tag
    RESTIC_TAGS+=("--tag=excl:/$tag_path")
done

# RESTIC_CMD="restic -r \"$RESTIC_REPO\" --password-file=\"$RESTIC_PASSWORD_FILE\" backup \"$SNAPSHOT_BACKUP_PATH\" ${EXCLUDE_ARGS[*]} ${RESTIC_TAGS[*]}"
RESTIC_CMD="restic"
RESTIC_CMD+=" ${EXCLUDE_ARGS[*]}"
RESTIC_CMD+=" ${RESTIC_TAGS[*]}"
RESTIC_CMD+=" -r $RESTIC_REPO"
RESTIC_CMD+=" --password-file=$RESTIC_PASSWORD_FILE"
RESTIC_CMD+=" backup $SNAPSHOT_BACKUP_PATH"
RESTIC_CMD+=" --verbose"

run_or_echo "$DRY_RUN" "$RESTIC_CMD"

echo "🧹 Cleaning up..."
clean_up_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"

echo "✅ Data volume backup completed."
