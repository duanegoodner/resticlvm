#!/bin/bash

set -euo pipefail

# shellcheck disable=SC1091
source "$(dirname "$0")/backup_helpers.sh"

# ─── Require Running as Root ─────────────────────────────────────
root_check

# ─── Default Values ──────────────────────────────────────────────
BACKUP_SOURCE=""
RESTIC_REPO=""
RESTIC_PASSWORD_FILE=""
EXCLUDE_PATHS=""
REMOUNT_AS_RO="false"
DRY_RUN=false

# ─── Parse and Validate Arguments ─────────────────────────────────
parse_arguments usage_path "restic-repo password-file backup-source exclude-paths remount-as-ro dry-run" "$@"
validate_args usage_path_backup RESTIC_REPO RESTIC_PASSWORD_FILE BACKUP_SOURCE

# ─── Pre-checks ───────────────────────────────────────────────────
check_if_path_exists "$BACKUP_SOURCE"

# ─── Display Configuration ───────────────────────────────────────
display_config "Backup Configuration" \
    RESTIC_REPO RESTIC_PASSWORD_FILE BACKUP_SOURCE EXCLUDE_PATHS REMOUNT_AS_RO DRY_RUN

display_dry_run_message "$DRY_RUN"

# ─── Remount Read-Only if Needed ──────────────────────────────────
if [ "$REMOUNT_AS_RO" = true ]; then
    remount_as_read_only "$DRY_RUN" "$BACKUP_SOURCE"
fi

# ─── Build Restic Backup Command ──────────────────────────────────
EXCLUDE_ARGS=()
populate_exclude_paths EXCLUDE_ARGS "$EXCLUDE_PATHS"

RESTIC_TAGS=()
populate_restic_tags RESTIC_TAGS "$EXCLUDE_PATHS"

RESTIC_CMD="restic -r $RESTIC_REPO --password-file=$RESTIC_PASSWORD_FILE"
RESTIC_CMD+=" ${EXCLUDE_ARGS[*]}"
RESTIC_CMD+=" ${RESTIC_TAGS[*]}"
RESTIC_CMD+=" backup $BACKUP_SOURCE"
RESTIC_CMD+=" --verbose"

# ─── Run Restic Backup ────────────────────────────────────────────
echo "🚀 Running Restic backup..."
run_or_echo "$DRY_RUN" "$RESTIC_CMD"

# ─── Remount Back to Read-Write if Needed ─────────────────────────
if [ "$REMOUNT_AS_RO" = true ]; then
    remount_as_read_write "$DRY_RUN" "$BACKUP_SOURCE"
fi

# ─── Done ─────────────────────────────────────────────────────────
echo "✅ Backup completed (or would have, in dry-run mode)."
