#!/bin/bash

# Ensure script runs as root (even in dry-run)
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root or with sudo."
    exit 1
fi

# ─── Default values ───────────────────────────────────────────────
EXCLUDE_PATHS="/dev /media /mnt /proc /run /sys /tmp /var/tmp /var/lib/libvirt/images"
BACKUP_SOURCE="/" # Inside chroot
DRY_RUN=false
DRY_RUN_PREFIX="\033[1;33m[DRY RUN]\033[0m"
CHROOT_REPO_PATH="/.restic_repo"

# ─── Parse named + short arguments ────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
    --vg-name | -g)
        VG_NAME="$2"
        shift 2
        ;;
    --lv-name | -l)
        LV_NAME="$2"
        shift 2
        ;;
    --snap-size | -z)
        SNAP_SIZE="$2"
        shift 2
        ;;
    --restic-repo | -r)
        RESTIC_REPO="$2"
        shift 2
        ;;
    --password-file | -p)
        RESTIC_PASSWORD_FILE="$2"
        shift 2
        ;;
    --exclude-paths | -e)
        EXCLUDE_PATHS="$2"
        shift 2
        ;;
    --backup-source | -s)
        BACKUP_SOURCE="$2"
        shift 2
        ;;
    --dry-run | -n)
        DRY_RUN=true
        shift
        ;;
    *)
        echo "❌ Unknown option: $1"
        exit 1
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

    if [[ "$missing" -eq 1 ]]; then
        echo ""
        echo "Usage:"
        echo "  $0 -g VG -l LV -z SIZE -r REPO -p PASSFILE [-e EXCLUDES] [-s SRC] [-n]"
        echo ""
        echo "Options:"
        echo "  -g, --vg-name          Volume group name"
        echo "  -l, --lv-name          Logical volume name"
        echo "  -z, --snap-size        Snapshot size (e.g., 1G)"
        echo "  -r, --restic-repo      Restic repository path"
        echo "  -p, --password-file    Path to password file"
        echo "  -e, --exclude-paths    Space-separated paths to exclude"
        echo "  -s, --backup-source    Path inside snapshot to back up (default: /)"
        echo "  -n, --dry-run          Dry run mode (preview only)"
        exit 1
    fi
}

validate_args

# ─── Generate names based on timestamp ────────────────────────────
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SNAP_NAME="${VG_NAME}_${LV_NAME}_${TIMESTAMP}"
SNAPSHOT_MOUNT_POINT="/srv/${SNAP_NAME}_for_restic"
CHROOT_REPO_FULL="$CHROOT_REPO_PATH/$(basename "$RESTIC_REPO")"
EXCLUDE_PATHS="$CHROOT_REPO_PATH $EXCLUDE_PATHS"

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

# ─── Dry-run aware runner ─────────────────────────────────────────
run_or_echo() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${DRY_RUN_PREFIX} $*"
    else
        eval "$@"
    fi
}

# ─── Pre-check: does the backup source exist now if mounted? ──────
LV_PATH="/dev/$VG_NAME/$LV_NAME"
CURRENT_MOUNT=$(findmnt -n -o TARGET --source "$LV_PATH")

if [ -n "$CURRENT_MOUNT" ]; then
    TEST_PATH="$CURRENT_MOUNT$BACKUP_SOURCE"
    if [ ! -e "$TEST_PATH" ]; then
        echo "❌ Error: Backup source $BACKUP_SOURCE does not exist under currently mounted $LV_PATH"
        echo "   → Checked path: $TEST_PATH"
        echo "💡 Tip: If this LV isn't mounted, this check may be unreliable."
        exit 1
    else
        echo "✅ Pre-check passed: found path $TEST_PATH"
    fi
else
    echo "ℹ️  LV $LV_PATH is not currently mounted. Skipping pre-check."
fi

# ─── Create and mount snapshot ────────────────────────────────────
echo "📸 Creating LVM snapshot..."
run_or_echo "lvcreate --size $SNAP_SIZE --snapshot --name $SNAP_NAME /dev/$VG_NAME/$LV_NAME"

echo "📂 Mounting snapshot..."
run_or_echo "mkdir -p \"$SNAPSHOT_MOUNT_POINT\""
run_or_echo "mount /dev/$VG_NAME/$SNAP_NAME \"$SNAPSHOT_MOUNT_POINT\""

# ─── Bind mount Restic repo and chroot essentials ────────────────
echo "🪝 Binding Restic repo into chroot..."
run_or_echo "mkdir -p \"$SNAPSHOT_MOUNT_POINT/$CHROOT_REPO_FULL\""
run_or_echo "mount --bind \"$RESTIC_REPO\" \"$SNAPSHOT_MOUNT_POINT/$CHROOT_REPO_FULL\""

echo "🔧 Preparing chroot environment..."
for path in /dev /proc /sys; do
    run_or_echo "mount --bind \"$path\" \"$SNAPSHOT_MOUNT_POINT$path\""
done

# ─── Validate backup source path inside snapshot ─────────────────
if [ "$DRY_RUN" = false ] && [ ! -e "$SNAPSHOT_MOUNT_POINT$BACKUP_SOURCE" ]; then
    echo "❌ Error: Backup source $BACKUP_SOURCE does not exist inside snapshot."
    echo "   → Checked: $SNAPSHOT_MOUNT_POINT$BACKUP_SOURCE"
    exit 1
fi

# ─── Build and run Restic backup ─────────────────────────────────
echo "🚀 Running Restic backup in chroot..."

EXCLUDE_ARGS=""
for path in $EXCLUDE_PATHS; do
    EXCLUDE_ARGS+="--exclude=$path "
done

RESTIC_CMD="export RESTIC_PASSWORD_FILE=$RESTIC_PASSWORD_FILE && restic $EXCLUDE_ARGS -r $CHROOT_REPO_FULL backup $BACKUP_SOURCE --verbose"

if [ "$DRY_RUN" = true ]; then
    echo -e "${DRY_RUN_PREFIX} Would run in chroot: $RESTIC_CMD"
else
    chroot "$SNAPSHOT_MOUNT_POINT" /bin/bash -c "$RESTIC_CMD"
fi

# ─── Cleanup ──────────────────────────────────────────────────────
echo "🧹 Cleaning up..."

run_or_echo "umount \"$SNAPSHOT_MOUNT_POINT/$CHROOT_REPO_FULL\""
for path in /dev /proc /sys; do
    run_or_echo "umount \"$SNAPSHOT_MOUNT_POINT$path\""
done
run_or_echo "umount \"$SNAPSHOT_MOUNT_POINT\""
run_or_echo "lvremove -y \"/dev/$VG_NAME/$SNAP_NAME\""
run_or_echo "rmdir \"$SNAPSHOT_MOUNT_POINT\""

echo "✅ Backup completed (or would have, in dry-run mode)."
