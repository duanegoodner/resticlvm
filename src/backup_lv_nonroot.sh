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
BACKUP_SOURCE=""
EXCLUDE_PATHS=""
DRY_RUN=false

# ─── Parse and Validate Arguments ─────────────────────────────────
parse_arguments usage_lv_nonroot "vg-name lv-name snap-size restic-repo password-file backup-source exclude-paths dry-run" "$@"
validate_args usage_lv_nonroot VG_NAME LV_NAME SNAP_SIZE RESTIC_REPO RESTIC_PASSWORD_FILE

# ### SET TIMESTAMP-BASED VARIABLES ###########################
SNAP_NAME=$(generate_snapshot_name "$VG_NAME" "$LV_NAME")
LV_DEVICE_PATH="/dev/$VG_NAME/$LV_NAME"

# ### PRE-CHECKS ###############################################

# Does the logical volume exist?
check_device_path "$LV_DEVICE_PATH"

# Is the logical volume mounted and where?
LV_MOUNT_POINT=$(check_mount_point "$LV_DEVICE_PATH")

# Does the backup source exist under the mount point?
confirm_source_in_lv "$LV_MOUNT_POINT" "$BACKUP_SOURCE"

SNAPSHOT_MOUNT_POINT="/srv${LV_MOUNT_POINT}"

REL_PATH="${BACKUP_SOURCE#$LV_MOUNT_POINT}"
SNAPSHOT_BACKUP_PATH="$SNAPSHOT_MOUNT_POINT$REL_PATH"

# Confirm that intended snapshot mount point does not already exist
confirm_not_yet_exist_snapshot_mount_point "$SNAPSHOT_MOUNT_POINT"

# ### DISPLAY PRE-RUN INFO ######################################
# display_snapshot_backup_config
display_config "LVM Snapshot Backup Configuration" \
    VG_NAME LV_NAME SNAP_SIZE SNAP_NAME SNAPSHOT_MOUNT_POINT \
    RESTIC_REPO RESTIC_PASSWORD_FILE EXCLUDE_PATHS BACKUP_SOURCE DRY_RUN
display_dry_run_message "$DRY_RUN"

# ### CREATE AND MOUNT SNAPSHOT ###############################
create_snapshot "$DRY_RUN" "$SNAP_SIZE" "$SNAP_NAME" "$VG_NAME" "$LV_NAME"
mount_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"

EXCLUDE_ARGS=()
polulate_exclude_paths_for_lv_nonroot EXCLUDE_ARGS "$EXCLUDE_PATHS" "$SNAPSHOT_MOUNT_POINT"
RESTIC_TAGS=()
populate_restic_tags_for_lv_nonroot RESTIC_TAGS "$EXCLUDE_PATHS" "$SNAPSHOT_MOUNT_POINT"

RESTIC_CMD="restic -r $RESTIC_REPO"
RESTIC_CMD+=" --password-file=$RESTIC_PASSWORD_FILE"
RESTIC_CMD+=" backup $SNAPSHOT_BACKUP_PATH"
RESTIC_CMD+=" ${EXCLUDE_ARGS[*]}"
RESTIC_CMD+=" ${RESTIC_TAGS[*]}"
RESTIC_CMD+=" --verbose"

run_or_echo "$DRY_RUN" "$RESTIC_CMD"

clean_up_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"

echo "✅ Backup completed (or would have, in dry-run mode)."
