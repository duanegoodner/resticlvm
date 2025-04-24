#!/bin/bash

set -euo pipefail

# ─── Root Check ────────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root or with sudo."
    exit 1
fi

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

usage() {
    echo "Usage:"
    echo "$0 -g VG -l LV -z SIZE -r REPO -p PASSFILE -e EXCLUDES -s SRC  [-n]"
    echo ""
    echo "Options:"
    echo "  -g, --vg-name          Volume group name"
    echo "  -l, --lv-name          Logical volume name"
    echo "  -z, --snap-size        Snapshot size (e.g., 1G)"
    echo "  -r, --restic-repo      Restic repository path"
    echo "  -p, --password-file    Path to password file"
    echo "  -e, --exclude-paths    Space-separated paths to exclude"
    echo "  -s, --backup-source    Path inside snapshot to back up"
    echo "  -n, --dry-run          Dry run mode (preview only)"
    echo "  -h, --help             Display this message and exit"
    exit 1
}

# ─── Parse named + short arguments ────────────────────────────────

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
    -n | --dry-run)
        DRY_RUN=true
        shift
        ;;
    -h | --help) usage ;;
    *)
        echo "❌ Unknown option: $1"
        usage
        ;;
    esac
done

# ─── Validate required inputs ─────────────────────────────────────

validate_args() {
    local missing=0

    if [[ -z "$VG_NAME" ]]; then
        echo "❌ Error: --vg-name is required"
        missing=1
    fi
    if [[ -z "$LV_NAME" ]]; then
        echo "❌ Error: --lv-name is required"
        missing=1
    fi
    if [[ -z "$SNAP_SIZE" ]]; then
        echo "❌ Error: --snap-size is required"
        missing=1
    fi
    if [[ -z "$RESTIC_REPO" ]]; then
        echo "❌ Error: --restic-repo is required"
        missing=1
    fi
    if [[ -z "$RESTIC_PASSWORD_FILE" ]]; then
        echo "❌ Error: --password-file is required"
        missing=1
    fi
    if [[ -z "$BACKUP_SOURCE" ]]; then
        echo "❌ Error: --backup-source is required"
        missing=1
    fi
    if [[ "$missing" -eq 1 ]]; then
        usage
    fi
}

validate_args

# ─── Pre-check: does lhe logical volue exist  ──────
LV_DEVICE_PATH="/dev/$VG_NAME/$LV_NAME"

if ! [ -e "$LV_DEVICE_PATH" ]; then
    echo "❌ Logical volume $LV_DEVICE_PATH does not exist."
    exit 1
fi

# ─── Pre-check: is the LV mounted? ──────
LV_MOUNT_POINT=$(findmnt -n -o TARGET --source "$LV_DEVICE_PATH")

if [ -n "$LV_MOUNT_POINT" ]; then
    echo "ℹ️  LV $LV_DEVICE_PATH is currently mounted at $LV_MOUNT_POINT."
else
    echo "❌  LV $LV_DEVICE_PATH is not currently mounted but must be mounted for backup."
    echo "   → Please mount it before running this script."
    echo "   → Example: mount $LV_DEVICE_PATH /mnt."
    echo "   → Exiting."
    exit 1
fi

# ─── Generate names based on timestamp ────────────────────────────
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SNAP_NAME="${VG_NAME}_${LV_NAME}_snapshot_${TIMESTAMP}"
SNAPSHOT_MOUNT_POINT="/srv${SNAP_NAME}"
REL_PATH="${BACKUP_SOURCE#$LV_MOUNT_POINT}"
SNAPSHOT_BACKUP_PATH="$SNAPSHOT_MOUNT_POINT$REL_PATH"

# if [[ -z "$BACKUP_SOURCE" ]]; then
#     BACKUP_SOURCE="$LV_MOUNT_POINT"
# fi

# ─── Pre-check: does source path exist under logical volume mount point  ──────
# Resolve real paths
REAL_MOUNT=$(realpath "$LV_MOUNT_POINT")
REAL_BACKUP=$(realpath -m "$BACKUP_SOURCE")

if [[ "$REAL_BACKUP" != "$REAL_MOUNT"* ]]; then
    echo "❌ Error: Backup source '$BACKUP_SOURCE' is not within logical volume mount point '$REAL_MOUNT'"
    echo "   → Resolved path: $REAL_BACKUP"
    exit 1
elif [[ ! -e "$REAL_BACKUP" ]]; then
    echo "❌ Error: Backup source path '$REAL_BACKUP' does not exist."
    exit 1
else
    echo "✅ Backup source $BACKUP_SOURCE resolves to $REAL_BACKUP and is valid."
fi

# ─── Pre-check: does the snapshot mount point already exist? ──────
if [[ -e "$SNAPSHOT_MOUNT_POINT" ]]; then
    echo "❌ Mount point $SNAPSHOT_MOUNT_POINT already exists. Aborting."
    exit 1
fi

# ─── Show config summary ──────────────────────────────────────────
echo ""
echo "🧾 LVM Snapshot Backup Configuration:"
echo "  Volume group:          $VG_NAME"
echo "  Logical volume:        $LV_NAME"
echo "  Snapshot size:         $SNAP_SIZE"
echo "  Snapshot name:         $SNAP_NAME"
echo "  Mount point:           $SNAPSHOT_MOUNT_POINT"
echo "  Restic repo:           $RESTIC_REPO"
echo "  Password file:         $RESTIC_PASSWORD_FILE"
echo "  Exclude paths:         $EXCLUDE_PATHS"
echo "  Backup source:         $BACKUP_SOURCE"
echo "  Dry run:               $DRY_RUN"

if [ "$DRY_RUN" = true ]; then
    echo -e "\n🟡 ${DRY_RUN_PREFIX} The following describes what *would* happen if this were a real backup run.\n"
fi

# ─── Dry Run Wrapper ───────────────────────────────────────────
run_or_echo() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${DRY_RUN_PREFIX} $*"
    else
        eval "$@"
    fi
}

EXCLUDE_ARGS=()
RESTIC_TAGS=()
for path in $EXCLUDE_PATHS; do
    rel="${path#$LV_MOUNT_POINT}"
    abs="$SNAPSHOT_MOUNT_POINT$rel"
    EXCLUDE_ARGS+=("--exclude=$abs")

    tag_path="${rel#/}" # Remove leading slash for tag
    RESTIC_TAGS+=("--tag=excl:/$tag_path")
done

echo "📸 Creating snapshot..."
run_or_echo "lvcreate --size \"$SNAP_SIZE\" --snapshot --name \"$SNAP_NAME\" \"/dev/$VG_NAME/$LV_NAME\""

echo "📂 Mounting snapshot..."
run_or_echo "mkdir -p \"$SNAPSHOT_MOUNT_POINT\""
run_or_echo "mount \"/dev/$VG_NAME/$SNAP_NAME\" \"$SNAPSHOT_MOUNT_POINT\""

echo "🚀 Running Restic backup..."

RESTIC_CMD="restic -r \"$RESTIC_REPO\" --password-file=\"$RESTIC_PASSWORD_FILE\" backup \"$SNAPSHOT_BACKUP_PATH\" ${EXCLUDE_ARGS[*]} ${RESTIC_TAGS[*]}"

run_or_echo "$RESTIC_CMD"

echo "🧹 Cleaning up..."
run_or_echo "umount \"$SNAPSHOT_MOUNT_POINT\""
run_or_echo "lvremove -y \"/dev/$VG_NAME/$SNAP_NAME\""
run_or_echo "rmdir \"$SNAPSHOT_MOUNT_POINT\""

echo "✅ Data volume backup completed."
