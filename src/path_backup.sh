#!/bin/bash

# Ensure we run as root (even in dry run mode)
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root or with sudo."
    exit 1
fi

# Default values
EXCLUDE_PATHS=""
REMOUNT_AS_RO="false"
DRY_RUN=false
DRY_RUN_PREFIX="\033[1;33m[DRY RUN]\033[0m"

# ─── Argument parsing ──────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
    --restic-repo | -r)
        RESTIC_REPO="$2"
        shift 2
        ;;
    --password-file | -p)
        RESTIC_PASSWORD_FILE="$2"
        shift 2
        ;;
    --backup-source | -s)
        BACKUP_SOURCE="$2"
        shift 2
        ;;
    --exclude-paths | -e)
        EXCLUDE_PATHS="$2"
        shift 2
        ;;
    --remount-as-ro | -m)
        REMOUNT_AS_RO="$2"
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

# ─── Validation ─────────────────────────────────────────────────────
validate_args() {
    local missing=0

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
        echo ""
        echo "Usage:"
        echo "  $0 -r PATH -p FILE -s PATH [-e PATHS] [-m true|false] [-n]"
        echo ""
        echo "Options:"
        echo "  -r, --restic-repo       Path to Restic repository"
        echo "  -p, --password-file     Path to password file"
        echo "  -s, --backup-source     Path to back up"
        echo "  -e, --exclude-paths     Space-separated paths to exclude"
        echo "  -m, --remount-as-ro     true or false (default: false)"
        echo "  -n, --dry-run           Dry run mode (preview only)"
        exit 1
    fi
}

validate_args

# ─── Print backup summary ───────────────────────────────────────────
echo ""
echo "🧾 Backup Configuration:"
echo "  Restic repo:          $RESTIC_REPO"
echo "  Password file:        $RESTIC_PASSWORD_FILE"
echo "  Backup source:        $BACKUP_SOURCE"
echo "  Exclude paths:        $EXCLUDE_PATHS"
echo "  Remount as read-only: $REMOUNT_AS_RO"
echo "  Dry run:              $DRY_RUN"

if [ "$DRY_RUN" = true ]; then
    echo -e "\n🟡 ${DRY_RUN_PREFIX} The following describes what *would* happen if this were a real backup run.\n"
fi

# ─── Dry-run aware wrapper ──────────────────────────────────────────
run_or_echo() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${DRY_RUN_PREFIX} $*"
    else
        eval "$@"
    fi
}

# ─── Optionally remount read-only ──────────────────────────────────
if [ "$REMOUNT_AS_RO" = true ]; then
    if ! mountpoint -q "$BACKUP_SOURCE"; then
        echo -e "⚠️  $BACKUP_SOURCE is not a mount point. Skipping remount."
    else
        PARTITION_DEV=$(findmnt -n -o SOURCE --target "$BACKUP_SOURCE")
        echo "🔒 Remounting $PARTITION_DEV (mounted at $BACKUP_SOURCE) as read-only..."
        run_or_echo "mount -o remount,ro \"$PARTITION_DEV\""
    fi
fi

# ─── Convert exclude paths to Restic-compatible format ─────────────
EXCLUDE_ARGS=()
for path in $EXCLUDE_PATHS; do
    EXCLUDE_ARGS+=("--exclude=$path")
done

# ─── Run the backup ────────────────────────────────────────────────
echo "🚀 Running Restic backup..."

RESTIC_CMD="restic -r \"$RESTIC_REPO\" --password-file=\"$RESTIC_PASSWORD_FILE\" backup \"$BACKUP_SOURCE\" ${EXCLUDE_ARGS[*]} --verbose"

if [ "$DRY_RUN" = true ]; then
    echo -e "${DRY_RUN_PREFIX} Would run: $RESTIC_CMD"
else
    eval "$RESTIC_CMD"
    if [ $? -ne 0 ]; then
        echo "❌ Restic backup failed."
    fi
fi

# ─── Optionally remount back to read-write ─────────────────────────
if [ "$REMOUNT_AS_RO" = true ] && mountpoint -q "$BACKUP_SOURCE"; then
    PARTITION_DEV=$(findmnt -n -o SOURCE --target "$BACKUP_SOURCE")
    echo "🔓 Remounting $PARTITION_DEV (mounted at $BACKUP_SOURCE) as read-write..."
    run_or_echo "mount -o remount,rw \"$PARTITION_DEV\""
fi
