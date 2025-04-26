#!/bin/bash

set -euo pipefail

# shellcheck disable=SC1091
source "$(dirname "$0")/backup_helpers.sh"

# ### REQUIRE RUNNING AS ROOT / SUDO ###########################
root_check

# ### SET DEFAULT VALUES #######################################
VG_NAME=""
LV_NAME=""
SNAP_SIZE=""
RESTIC_REPO=""
RESTIC_PASSWORD_FILE=""
BACKUP_SOURCE=""
EXCLUDE_PATHS=""
DRY_RUN=false

CHROOT_REPO_PATH="/.restic_repo"

# ### COLLECT AND VALUDATE ARGUMENTS ###########################
parse_arguments usage_lv_nonroot "vg-name lv-name snap-size restic-repo password-file backup-source exclude-paths dry-run" "$@"
validate_args usage_lv_nonroot VG_NAME LV_NAME SNAP_SIZE RESTIC_REPO RESTIC_PASSWORD_FILE

# ### SET TIMESTAMP-BASED VARIABLES ###########################
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SNAP_NAME="${VG_NAME}_${LV_NAME}_${TIMESTAMP}"

# Define LV_DEVICE_PATH now that VG_NAME and LV_NAME are set
LV_DEVICE_PATH="/dev/$VG_NAME/$LV_NAME"

# ### PRE-CHECKS ###############################################

# Does the logical volume exist?
check_device_path "$LV_DEVICE_PATH"

# Is the logical volume mounted and where?
LV_MOUNT_POINT=$(check_mount_point "$LV_DEVICE_PATH")

# Check if the logical volume is mounted at root
IS_MOUNTED_AT_ROOT=false
if [ "$LV_MOUNT_POINT" == "/" ]; then
    IS_MOUNTED_AT_ROOT=true
fi

# Set the snapshot mount point based on whether it's mounted at root
if [ "$IS_MOUNTED_AT_ROOT" = true ]; then
    SNAPSHOT_MOUNT_POINT="/srv/${SNAP_NAME}"
else
    SNAPSHOT_MOUNT_POINT="/srv${LV_MOUNT_POINT}"
    REL_PATH="${BACKUP_SOURCE#$LV_MOUNT_POINT}"
    SNAPSHOT_BACKUP_PATH="$SNAPSHOT_MOUNT_POINT$REL_PATH"
fi

# Compute paths based on mount point
REAL_MOUNT=$(realpath "$LV_MOUNT_POINT")
REAL_BACKUP=$(realpath -m "$BACKUP_SOURCE")

# Does the backup source exist under the mount point?
confirm_source_in_lv "$REAL_BACKUP" "$REAL_MOUNT" "$BACKUP_SOURCE"

# ### DISPLAY PRE-RUN INFO ######################################
# display_snapshot_backup_config
display_config "LVM Snapshot Backup Configuration" \
    VG_NAME LV_NAME SNAP_SIZE SNAP_NAME SNAPSHOT_MOUNT_POINT \
    RESTIC_REPO RESTIC_PASSWORD_FILE EXCLUDE_PATHS BACKUP_SOURCE DRY_RUN
display_dry_run_message "$DRY_RUN"

# ### CREATE AND MOUNT SNAPSHOT ###############################
create_snapshot "$DRY_RUN" "$SNAP_SIZE" "$SNAP_NAME" "$VG_NAME" "$LV_NAME"
mount_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"

if [ "$IS_MOUNTED_AT_ROOT" = true ]; then
    # ### SET BINDINGS #########################################
    CHROOT_REPO_FULL="$CHROOT_REPO_PATH/$(basename "$RESTIC_REPO")"
    bind_repo_to_mounted_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$RESTIC_REPO" "$CHROOT_REPO_FULL"
    bind_chroot_essentials_to_mounted_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT"
fi

if [ "$IS_MOUNTED_AT_ROOT" = true ]; then
    ### UNDO BINDINGS USED FOR CHROOT #########################
    unmount_chroot_bindings "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$CHROOT_REPO_FULL"
fi

clean_up_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"
