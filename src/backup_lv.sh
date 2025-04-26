#!/bin/bash

set -euo pipefail

# shellcheck disable=SC1091
source "$(dirname "$0")/backup_helpers.sh"
source "$(dirname "$0")/arg_handlers.sh"
source "$(dirname "$0")/command_builders.sh"
source "$(dirname "$0")/command_runners.sh"
source "$(dirname "$0")/pre_checks.sh"
source "$(dirname "$0")/lv_snapshots.sh"
source "$(dirname "$0")/mounts.sh"
source "$(dirname "$0")/usage_commands.sh"
source "$(dirname "$0")/message_display.sh"

# ### REQUIRE ROOT #########################################
root_check

# ### DEFAULTS #############################################
VG_NAME=""
LV_NAME=""
SNAP_SIZE=""
RESTIC_REPO=""
RESTIC_PASSWORD_FILE=""
BACKUP_SOURCE="/" # Default inside snapshot
EXCLUDE_PATHS="/dev /media /mnt /proc /run /sys /tmp /var/tmp /var/lib/libvirt/images"
DRY_RUN=false
CHROOT_REPO_PATH="/.restic_repo"

# ### TIMESTAMP #############################################
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# ### PARSE ARGS ###########################################
parse_arguments usage_lv_root "$@"
validate_args usage_lv_root

LV_DEVICE_PATH="/dev/$VG_NAME/$LV_NAME"

# ### PRE-CHECKS ###########################################
check_device_path "$LV_DEVICE_PATH"
LV_MOUNT_POINT=$(check_mount_point "$LV_DEVICE_PATH")

REAL_MOUNT=$(realpath "$LV_MOUNT_POINT")
REAL_BACKUP=$(realpath -m "$BACKUP_SOURCE")

confirm_source_in_lv "$REAL_BACKUP" "$REAL_MOUNT" "$BACKUP_SOURCE"

SNAP_NAME="${VG_NAME}_${LV_NAME}_snapshot_${TIMESTAMP}"
SNAPSHOT_MOUNT_POINT="/srv/${SNAP_NAME}"
confirm_not_yet_exist_snapshot_mount_point "$SNAPSHOT_MOUNT_POINT"

# ### DETERMINE MODE ######################################
if [[ "$LV_MOUNT_POINT" == "/" ]]; then
    MODE="root"
else
    MODE="nonroot"
fi

# ### DISPLAY #############################################
display_snapshot_backup_config

if [ "$DRY_RUN" = true ]; then
    display_dry_run_message "$DRY_RUN"
fi

# ### SNAPSHOT + MOUNT #####################################
create_snapshot "$DRY_RUN" "$SNAP_SIZE" "$SNAP_NAME" "$VG_NAME" "$LV_NAME"
mount_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"

# ### PREPARE RESTIC COMMAND ##############################
EXCLUDE_ARGS=()
RESTIC_TAGS=()

if [[ "$MODE" == "root" ]]; then
    # Root mode: bind restic repo and essentials
    bind_repo_to_mounted_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$RESTIC_REPO"
    bind_chroot_essentials_to_mounted_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT"

    CHROOT_REPO_FULL="$CHROOT_REPO_PATH/$(basename "$RESTIC_REPO")"
    EXCLUDE_PATHS="$CHROOT_REPO_PATH $EXCLUDE_PATHS"
    populate_exclude_paths EXCLUDE_ARGS "$EXCLUDE_PATHS"
    populate_restic_tags RESTIC_TAGS "$EXCLUDE_PATHS"

    RESTIC_CMD="export RESTIC_PASSWORD_FILE=$RESTIC_PASSWORD_FILE && restic"
    RESTIC_CMD+=" ${EXCLUDE_ARGS[*]}"
    RESTIC_CMD+=" ${RESTIC_TAGS[*]}"
    RESTIC_CMD+=" -r $CHROOT_REPO_FULL"
    RESTIC_CMD+=" backup $BACKUP_SOURCE"
    RESTIC_CMD+=" --verbose"

    echo "🚀 Running Restic backup inside chroot..."
    run_in_chroot_or_echo "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$RESTIC_CMD"

else
    # Non-root mode: backup subpath inside snapshot
    REL_PATH="${BACKUP_SOURCE#$LV_MOUNT_POINT}"
    SNAPSHOT_BACKUP_PATH="$SNAPSHOT_MOUNT_POINT$REL_PATH"

    populate_exclude_paths EXCLUDE_ARGS "$EXCLUDE_PATHS"
    populate_restic_tags RESTIC_TAGS "$EXCLUDE_PATHS"

    RESTIC_CMD="restic"
    RESTIC_CMD+=" ${EXCLUDE_ARGS[*]}"
    RESTIC_CMD+=" ${RESTIC_TAGS[*]}"
    RESTIC_CMD+=" -r $RESTIC_REPO"
    RESTIC_CMD+=" --password-file=$RESTIC_PASSWORD_FILE"
    RESTIC_CMD+=" backup $SNAPSHOT_BACKUP_PATH"
    RESTIC_CMD+=" --verbose"

    echo "🚀 Running Restic backup..."
    run_or_echo "$DRY_RUN" "$RESTIC_CMD"
fi

# ### CLEANUP #############################################
if [[ "$MODE" == "root" ]]; then
    run_or_echo "$DRY_RUN" "umount \"$SNAPSHOT_MOUNT_POINT/$CHROOT_REPO_FULL\""
    for path in /dev /proc /sys; do
        run_or_echo "$DRY_RUN" "umount \"$SNAPSHOT_MOUNT_POINT$path\""
    done
fi

clean_up_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"

echo "✅ Backup completed (or would have, in dry-run mode)."
