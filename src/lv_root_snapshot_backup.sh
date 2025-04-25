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
BACKUP_SOURCE="/" # Inside chroot
EXCLUDE_PATHS="/dev /media /mnt /proc /run /sys /tmp /var/tmp /var/lib/libvirt/images"
DRY_RUN=false
DRY_RUN_PREFIX="\033[1;33m[DRY RUN]\033[0m"

CHROOT_REPO_PATH="/.restic_repo"
REAL_BACKUP=$(realpath -m "$BACKUP_SOURCE")

# ─── Generate names based on timestamp ────────────────────────────
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SNAP_NAME="${VG_NAME}_${LV_NAME}_snapshot_${TIMESTAMP}"
SNAPSHOT_MOUNT_POINT="/srv/${SNAP_NAME}"

parse_arguments usage_lv_root "$@"
validate_args usage_lv_root
# Define LV_DEVICE_PATH now that VG_NAME and LV_NAME are set
LV_DEVICE_PATH="/dev/$VG_NAME/$LV_NAME"

# ─── Pre-check: does lhe logical volue exist  ──────

check_device_path "$LV_DEVICE_PATH"

# ─── Pre-check: is the logical volume mounted  ──────
LV_MOUNT_POINT=$(check_mount_point "$LV_DEVICE_PATH")

# Now LV_MOUNT_POINT contains only the mount point and can be used safely
REAL_MOUNT=$(realpath "$LV_MOUNT_POINT")

CHROOT_REPO_FULL="$CHROOT_REPO_PATH/$(basename "$RESTIC_REPO")"
EXCLUDE_PATHS="$CHROOT_REPO_PATH $EXCLUDE_PATHS"

confirm_source_in_lv "$REAL_BACKUP" "$REAL_MOUNT" "$BACKUP_SOURCE"

confirm_not_yet_exist_snapshot_mount_point "$SNAPSHOT_MOUNT_POINT"

display_snapshot_backup_config

display_dry_run_message "$DRY_RUN"

# ─── Create and mount snapshot ────────────────────────────────────
echo "📸 Creating LVM snapshot..."
run_or_echo "$DRY_RUN" "lvcreate --size $SNAP_SIZE --snapshot --name $SNAP_NAME /dev/$VG_NAME/$LV_NAME"

echo "📂 Mounting snapshot..."
run_or_echo "$DRY_RUN" "mkdir -p \"$SNAPSHOT_MOUNT_POINT\""
run_or_echo "$DRY_RUN" "mount /dev/$VG_NAME/$SNAP_NAME \"$SNAPSHOT_MOUNT_POINT\""

# ─── Bind mount Restic repo and chroot essentials ────────────────
echo "🪝 Binding Restic repo into chroot..."
run_or_echo "$DRY_RUN" "mkdir -p \"$SNAPSHOT_MOUNT_POINT/$CHROOT_REPO_FULL\""
run_or_echo "$DRY_RUN" "mount --bind \"$RESTIC_REPO\" \"$SNAPSHOT_MOUNT_POINT/$CHROOT_REPO_FULL\""

echo "🔧 Preparing chroot environment..."
for path in /dev /proc /sys; do
    run_or_echo "$DRY_RUN" "mount --bind \"$path\" \"$SNAPSHOT_MOUNT_POINT$path\""
done

# ─── Build and run Restic backup ─────────────────────────────────
echo "🚀 Running Restic backup in chroot..."

EXCLUDE_ARGS=()
RESTIC_TAGS=()
for path in $EXCLUDE_PATHS; do
    EXCLUDE_ARGS+=("--exclude=$path")

    tag_path="${path#/}" # Remove leading slash for tag
    RESTIC_TAGS+=("--tag=excl:/$tag_path")
done

RESTIC_CMD="export RESTIC_PASSWORD_FILE=$RESTIC_PASSWORD_FILE && restic"
RESTIC_CMD+=" ${EXCLUDE_ARGS[*]}"
RESTIC_CMD+=" ${RESTIC_TAGS[*]}"
RESTIC_CMD+=" -r $CHROOT_REPO_FULL"
RESTIC_CMD+=" backup $BACKUP_SOURCE"
RESTIC_CMD+=" --verbose"

if [ "$DRY_RUN" = true ]; then
    echo -e "${DRY_RUN_PREFIX} Would run in chroot: $RESTIC_CMD"
else
    chroot "$SNAPSHOT_MOUNT_POINT" /bin/bash -c "$RESTIC_CMD"
fi

# ─── Cleanup ──────────────────────────────────────────────────────
echo "🧹 Cleaning up..."

run_or_echo "$DRY_RUN" "umount \"$SNAPSHOT_MOUNT_POINT/$CHROOT_REPO_FULL\""
for path in /dev /proc /sys; do
    run_or_echo "$DRY_RUN" "umount \"$SNAPSHOT_MOUNT_POINT$path\""
done
run_or_echo "$DRY_RUN" "umount \"$SNAPSHOT_MOUNT_POINT\""
run_or_echo "$DRY_RUN" "lvremove -y \"/dev/$VG_NAME/$SNAP_NAME\""
run_or_echo "$DRY_RUN" "rmdir \"$SNAPSHOT_MOUNT_POINT\""

echo "✅ Backup completed (or would have, in dry-run mode)."
