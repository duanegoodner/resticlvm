#!/bin/bash

set -euo pipefail

SNAP_SIZE="300M"
DRY_RUN=false
EXCLUDE_PATHS=""

usage() {
    echo "Usage: $0 -g <vg_name> -l <lv_name> -r <restic_repo> -p <password_file> [-z <snap_size>] [-s <backup_source>] [-e \"path1 path2\"] [--dry-run]"
    exit 1
}

# Parse arguments
BACKUP_SOURCE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
    -g | --vg-name)
        VG_NAME="$2"
        shift 2
        ;;
    -l | --lv-name)
        LV_NAME="$2"
        shift 2
        ;;
    -z | --snap-size)
        SNAP_SIZE="$2"
        shift 2
        ;;
    -r | --restic-repo)
        RESTIC_REPO="$2"
        shift 2
        ;;
    -p | --password-file)
        RESTIC_PASSWORD_FILE="$2"
        shift 2
        ;;
    -s | --backup-source)
        BACKUP_SOURCE="$2"
        shift 2
        ;;
    -e | --exclude-paths)
        EXCLUDE_PATHS="$2"
        shift 2
        ;;
    --dry-run)
        DRY_RUN=true
        shift
        ;;
    -h | --help) usage ;;
    *)
        echo "Unknown option: $1"
        usage
        ;;
    esac
done

: "${VG_NAME:?Missing --vg-name}"
: "${LV_NAME:?Missing --lv-name}"
: "${RESTIC_REPO:?Missing --restic-repo}"
: "${RESTIC_PASSWORD_FILE:?Missing --password-file}"

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo."
    exit 1
fi

ORIGINAL_MOUNT_POINT=$(findmnt -n -o TARGET "/dev/$VG_NAME/$LV_NAME" || true)
if [[ -z "$ORIGINAL_MOUNT_POINT" ]]; then
    echo "❌ Error: /dev/$VG_NAME/$LV_NAME is not mounted."
    exit 1
fi

if [[ -z "$BACKUP_SOURCE" ]]; then
    BACKUP_SOURCE="$ORIGINAL_MOUNT_POINT"
fi

if [[ "$BACKUP_SOURCE" != "$ORIGINAL_MOUNT_POINT"* ]]; then
    echo "❌ Error: Backup source '$BACKUP_SOURCE' must be within '$ORIGINAL_MOUNT_POINT'"
    exit 1
fi

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SNAP_NAME="${VG_NAME}_${LV_NAME}_${TIMESTAMP}"
MOUNT_POINT="/srv${ORIGINAL_MOUNT_POINT}"

REL_PATH="${BACKUP_SOURCE#$ORIGINAL_MOUNT_POINT}"
SNAPSHOT_BACKUP_PATH="$MOUNT_POINT$REL_PATH"

EXCLUDE_ARGS=()
RESTIC_TAGS=()
for path in $EXCLUDE_PATHS; do
    rel="${path#$ORIGINAL_MOUNT_POINT}"
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
