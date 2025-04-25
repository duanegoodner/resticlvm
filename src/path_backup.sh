#!/bin/bash

set -euo pipefail

# shellcheck disable=SC1091
source "$(dirname "$0")/backup_helpers.sh"

# ### REQUIRE RUNNING AS ROOT / SUDO ###########################
root_check

# ### SET DEFAULT VALUES #######################################
BACKUP_SOURCE=""
RESTIC_REPO=""
RESTIC_PASSWORD_FILE=""
EXCLUDE_PATHS=""
REMOUNT_AS_RO="false"
DRY_RUN=false
DRY_RUN_PREFIX="\033[1;33m[DRY RUN]\033[0m"

# ### COLLECT AND VALUDATE ARGUMENTS ###########################
parse_arguments usage_path "restic-repo password-file backup-source exclude-paths remount-as-ro dry-run" "$@"
validate_args usage_path_backup RESTIC_REPO RESTIC_PASSWORD_FILE BACKUP_SOURCE

# ─── Summary ───────────────────────────────────────────────────
echo ""
echo "🧾 Backup Configuration:"
echo "  Restic repo:          $RESTIC_REPO"
echo "  Password file:        $RESTIC_PASSWORD_FILE"
echo "  Backup source:        $BACKUP_SOURCE"
echo "  Exclude paths:        $EXCLUDE_PATHS"
echo "  Remount as read-only: $REMOUNT_AS_RO"
echo "  Dry run:              $DRY_RUN"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "\n🟡 ${DRY_RUN_PREFIX} The following describes what *would* happen if this were a real backup run.\n"
fi

# ─── Check if backup source exists ─────────────────────────────
if [[ ! -e "$BACKUP_SOURCE" ]]; then
    echo "❌ Backup source path does not exist: $BACKUP_SOURCE"
    exit 1
fi

# ─── Dry Run Wrapper ───────────────────────────────────────────
run_or_echo() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "$DRY_RUN_PREFIX $*"
    else
        eval "$@"
    fi
}

# ─── Remount RO if needed ──────────────────────────────────────
if [ "$REMOUNT_AS_RO" = true ]; then
    if mountpoint -q "$BACKUP_SOURCE"; then
        DEV=$(findmnt -n -o SOURCE --target "$BACKUP_SOURCE")
        echo "🔒 Remounting $DEV as read-only..."
        run_or_echo "mount -o remount,ro $DEV"
    else
        echo "⚠️ $BACKUP_SOURCE is not a mount point. Skipping remount."
    fi
fi

# ─── Exclude Conversion ─────────────────────────────────────────
EXCLUDE_ARGS=()
populate_exclude_paths EXCLUDE_ARGS "$EXCLUDE_PATHS"

# ─── Restic Execution ───────────────────────────────────────────
echo "🚀 Running Restic backup..."
RESTIC_CMD="restic -r $RESTIC_REPO --password-file=$RESTIC_PASSWORD_FILE backup $BACKUP_SOURCE ${EXCLUDE_ARGS[*]} --verbose"

if [ "$DRY_RUN" = true ]; then
    echo -e "$DRY_RUN_PREFIX Would run: $RESTIC_CMD"
else
    eval "$RESTIC_CMD"
fi

# ─── Remount Back ───────────────────────────────────────────────
if [ "$REMOUNT_AS_RO" = true ] && mountpoint -q "$BACKUP_SOURCE"; then
    DEV=$(findmnt -n -o SOURCE --target "$BACKUP_SOURCE")
    echo "🔓 Remounting $DEV as read-write..."
    run_or_echo "mount -o remount,rw $DEV"
fi
