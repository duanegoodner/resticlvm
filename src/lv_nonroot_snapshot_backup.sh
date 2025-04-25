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

# ### COLLECT AND VALUDATE ARGUMENTS ###########################
parse_arguments usage_lv_nonroot "$@"
validate_args usage_lv_nonroot

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

confirm_source_in_lv "$REAL_BACKUP" "$REAL_MOUNT" "$BACKUP_SOURCE"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SNAP_NAME="${VG_NAME}_${LV_NAME}_${TIMESTAMP}"
MOUNT_POINT="/srv${LV_MOUNT_POINT}"

REL_PATH="${BACKUP_SOURCE#$LV_MOUNT_POINT}"
SNAPSHOT_BACKUP_PATH="$MOUNT_POINT$REL_PATH"

EXCLUDE_ARGS=()
RESTIC_TAGS=()
for path in $EXCLUDE_PATHS; do
    rel="${path#$LV_MOUNT_POINT}"
    abs="$MOUNT_POINT$rel"
    EXCLUDE_ARGS+=("--exclude=$abs")

    tag_path="${rel#/}" # Remove leading slash for tag
    RESTIC_TAGS+=("--tag=exclude:/$tag_path")
done

echo ""
echo "🧾 Data LV Backup Configuration:"
echo "  Volume group:     $VG_NAME"
echo "  Logical volume:   $LV_NAME"
echo "  Snapshot size:    $SNAP_SIZE"
echo "  Snapshot name:    $SNAP_NAME"
echo "  Snapshot mount:   $MOUNT_POINT"
echo "  Restic repo:      $RESTIC_REPO"
echo "  Password file:    $RESTIC_PASSWORD_FILE"
echo "  Backup source:    $BACKUP_SOURCE"
echo "  Exclude paths:    $EXCLUDE_PATHS"
echo "  Dry run:          $DRY_RUN"
echo ""

if [[ -e "$MOUNT_POINT" ]]; then
    echo "❌ Mount point $MOUNT_POINT already exists. Aborting."
    exit 1
fi

if [[ ! -e "$BACKUP_SOURCE" ]]; then
    echo "❌ Backup source $BACKUP_SOURCE does not exist. Aborting."
    exit 1
fi

if $DRY_RUN; then
    echo -e "\033[33m[DRY RUN] Would create snapshot: $SNAP_NAME\033[0m"
    echo -e "\033[33m[DRY RUN] Would mount snapshot at $MOUNT_POINT\033[0m"
    echo -e "\033[33m[DRY RUN] Would backup path: $SNAPSHOT_BACKUP_PATH\033[0m"
    echo -e "\033[33m[DRY RUN] Would run: restic -r \"$RESTIC_REPO\" --password-file=\"$RESTIC_PASSWORD_FILE\" backup \"$SNAPSHOT_BACKUP_PATH\" ${EXCLUDE_ARGS[*]} ${RESTIC_TAGS[*]}\033[0m"
    echo -e "\033[33m[DRY RUN] Would clean up mount + remove snapshot\033[0m"
    exit 0
fi

echo "📸 Creating snapshot..."
lvcreate --size "$SNAP_SIZE" --snapshot --name "$SNAP_NAME" "/dev/$VG_NAME/$LV_NAME"

echo "📂 Mounting snapshot..."
mkdir -p "$MOUNT_POINT"
mount "/dev/$VG_NAME/$SNAP_NAME" "$MOUNT_POINT"

echo "🚀 Running Restic backup..."
restic -r "$RESTIC_REPO" \
    --password-file="$RESTIC_PASSWORD_FILE" \
    backup "$SNAPSHOT_BACKUP_PATH" \
    "${EXCLUDE_ARGS[@]}" \
    "${RESTIC_TAGS[@]}"

echo "🧹 Cleaning up..."
umount "$MOUNT_POINT"
lvremove -y "/dev/$VG_NAME/$SNAP_NAME"
rmdir "$MOUNT_POINT"

echo "✅ Data volume backup completed."
