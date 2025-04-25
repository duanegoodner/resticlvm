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
BACKUP_SOURCE="/" # Inside chroot
EXCLUDE_PATHS="/dev /media /mnt /proc /run /sys /tmp /var/tmp /var/lib/libvirt/images"
DRY_RUN=false

CHROOT_REPO_PATH="/.restic_repo"

# ### SET TIMESTAMP-BASED VARIABLES ###########################
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SNAP_NAME="${VG_NAME}_${LV_NAME}_snapshot_${TIMESTAMP}"

# ### COLLECT AND VALUDATE ARGUMENTS ###########################
parse_arguments usage_lv_root "$@"
validate_args usage_lv_root

# Define LV_DEVICE_PATH now that VG_NAME and LV_NAME are set
LV_DEVICE_PATH="/dev/$VG_NAME/$LV_NAME"

# ### PRE-CHECKS ###############################################

# Does the logical volume exist?
check_device_path "$LV_DEVICE_PATH"

# Is the logical volume mounted and where?
LV_MOUNT_POINT=$(check_mount_point "$LV_DEVICE_PATH")

# Compute paths based on mount point
REAL_MOUNT=$(realpath "$LV_MOUNT_POINT")
REAL_BACKUP=$(realpath -m "$BACKUP_SOURCE")

# Does the backup source exist under the mount point?
confirm_source_in_lv "$REAL_BACKUP" "$REAL_MOUNT" "$BACKUP_SOURCE"

SNAPSHOT_MOUNT_POINT="/srv/${SNAP_NAME}"

# Confirm that intended snapshot mount point does not already exist
confirm_not_yet_exist_snapshot_mount_point "$SNAPSHOT_MOUNT_POINT"

# ### DISPLAY PRE-RUN INFO ######################################
display_snapshot_backup_config
display_dry_run_message "$DRY_RUN"

# ### CREATE AND MOUNT SNAPSHOT ###############################
create_snapshot "$DRY_RUN" "$SNAP_SIZE" "$SNAP_NAME" "$VG_NAME" "$LV_NAME"
mount_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"

# ### SET BINDINGS #########################################
CHROOT_REPO_FULL="$CHROOT_REPO_PATH/$(basename "$RESTIC_REPO")"
bind_repo_to_mounted_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$RESTIC_REPO" "$CHROOT_REPO_FULL"
bind_chroot_essentials_to_mounted_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT"

# ### BUILD RESTIC BACKUP COMMAND ########################
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

echo "🔍 Restic command: $RESTIC_CMD"

# ### RUN RESTIC BACKUP #####################################
echo "🚀 Running Restic backup in chroot..."
run_in_chroot_or_echo "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$RESTIC_CMD"

# ─── Cleanup ──────────────────────────────────────────────────────

run_or_echo "$DRY_RUN" "umount \"$SNAPSHOT_MOUNT_POINT/$CHROOT_REPO_FULL\""
for path in /dev /proc /sys; do
    run_or_echo "$DRY_RUN" "umount \"$SNAPSHOT_MOUNT_POINT$path\""
done

clean_up_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"

echo "✅ Backup completed (or would have, in dry-run mode)."
