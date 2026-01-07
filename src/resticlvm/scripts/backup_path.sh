#!/bin/bash

# Backup a standard filesystem path using Restic.
# Optionally remounts the source path as read-only during the backup.
#
# Arguments:
#   -r  Path to the Restic repository.
#   -p  Path to the Restic password file.
#   -s  Path to the backup source directory.
#   -e  (Optional) Comma-separated list of paths to exclude.
#   -m  (Optional) Remount the backup source as read-only during backup (true/false).
#   --dry-run  (Optional) Show actions without executing them.
#
# Usage:
#   This script is intended to be called internally by the ResticLVM tool.
#
# Requirements:
#   - Must be run with root privileges (direct root or via sudo).
#   - Restic must be installed and available in PATH.
#
# Exit codes:
#   0  Success
#   1  Any fatal error

set -euo pipefail

# shellcheck disable=SC1091
source "$(dirname "$0")/backup_helpers.sh"

# ─── Require Running as Root ─────────────────────────────────────
root_check

# ─── Default Values ──────────────────────────────────────────────
BACKUP_SOURCE_PATH=""
RESTIC_REPOS=()
RESTIC_PASSWORD_FILES=()
EXCLUDE_PATHS=""
REMOUNT_AS_RO="false"
DRY_RUN=false

# ─── Parse and Validate Arguments ─────────────────────────────────
parse_arguments usage_path "restic-repo password-file backup-source exclude-paths remount-as-ro dry-run" "$@"

# Validate basic args
validate_args usage_path_backup BACKUP_SOURCE_PATH

# Validate repository arrays
if [ ${#RESTIC_REPOS[@]} -eq 0 ]; then
    echo "❌ Error: At least one --restic-repo is required"
    usage_path
fi

if [ ${#RESTIC_REPOS[@]} -ne ${#RESTIC_PASSWORD_FILES[@]} ]; then
    echo "❌ Error: Number of repos (${#RESTIC_REPOS[@]}) must match number of password files (${#RESTIC_PASSWORD_FILES[@]})"
    usage_path
fi

# ─── Pre-checks ───────────────────────────────────────────────────
check_if_path_exists "$BACKUP_SOURCE_PATH"

# ─── Display Configuration ───────────────────────────────────────
display_config "Backup Configuration" \
    BACKUP_SOURCE_PATH EXCLUDE_PATHS REMOUNT_AS_RO DRY_RUN

echo "Repositories: ${#RESTIC_REPOS[@]}"
for i in "${!RESTIC_REPOS[@]}"; do
    echo "  $((i+1)). ${RESTIC_REPOS[$i]}"
done

display_dry_run_message "$DRY_RUN"

# ─── Remount Read-Only if Needed ──────────────────────────────────
if [ "$REMOUNT_AS_RO" = true ]; then
    remount_as_read_only "$DRY_RUN" "$BACKUP_SOURCE_PATH"
fi

# ─── Build Exclude Arguments (Once) ───────────────────────────────
EXCLUDE_ARGS=()
populate_exclude_paths EXCLUDE_ARGS "$EXCLUDE_PATHS"

RESTIC_TAGS=()
populate_restic_tags RESTIC_TAGS "$EXCLUDE_PATHS"

# ─── Loop Over Repositories ───────────────────────────────────────
echo "🚀 Backing up to ${#RESTIC_REPOS[@]} repository(ies)..."

for i in "${!RESTIC_REPOS[@]}"; do
    RESTIC_REPO="${RESTIC_REPOS[$i]}"
    RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILES[$i]}"
    
    echo ""
    echo "▶️  Repository $((i+1))/${#RESTIC_REPOS[@]}: $RESTIC_REPO"
    
    # Build Restic command for this repo
    RESTIC_CMD="restic -r $RESTIC_REPO --password-file=$RESTIC_PASSWORD_FILE"
    RESTIC_CMD+=" ${EXCLUDE_ARGS[*]}"
    RESTIC_CMD+=" ${RESTIC_TAGS[*]}"
    RESTIC_CMD+=" backup $BACKUP_SOURCE_PATH"
    RESTIC_CMD+=" --verbose"
    
    # Execute backup for this repo
    run_or_echo "$DRY_RUN" "$RESTIC_CMD"
done

# ─── Remount Back to Read-Write if Needed ─────────────────────────
if [ "$REMOUNT_AS_RO" = true ]; then
    remount_as_read_write "$DRY_RUN" "$BACKUP_SOURCE_PATH"
fi

# ─── Done ─────────────────────────────────────────────────────────
echo ""
echo "✅ Backup completed for ${#RESTIC_REPOS[@]} repository(ies) (or would have, in dry-run mode)."
