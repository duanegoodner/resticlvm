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

# ### COLLECT AND VALUDATE ARGUMENTS ###########################
parse_arguments usage_path "restic-repo password-file backup-source exclude-paths remount-as-ro dry-run" "$@"
validate_args usage_path_backup RESTIC_REPO RESTIC_PASSWORD_FILE BACKUP_SOURCE

# ### PRE-CHECKS ###############################################

# Check if the backup source exists
check_if_path_exists "$BACKUP_SOURCE"

# ### DISPLAY PRE-RUN INFO ######################################
display_config "Backup Configuration" \
    RESTIC_REPO RESTIC_PASSWORD_FILE BACKUP_SOURCE EXCLUDE_PATHS REMOUNT_AS_RO DRY_RUN
display_dry_run_message "$DRY_RUN"

# ### Remount RO if needed #####################################
if [ "$REMOUNT_AS_RO" = true ]; then
    remount_as_read_only "$DRY_RUN" "$BACKUP_SOURCE"
fi

# ### BUILD RESTIC BACKUP COMMAND ########################
EXCLUDE_ARGS=()
populate_exclude_paths EXCLUDE_ARGS "$EXCLUDE_PATHS"
RESTIC_TAGS=()
populate_restic_tags RESTIC_TAGS "$EXCLUDE_PATHS"

RESTIC_CMD="restic -r $RESTIC_REPO --password-file=$RESTIC_PASSWORD_FILE"
RESTIC_CMD+=" ${EXCLUDE_ARGS[*]}"
RESTIC_CMD+=" ${RESTIC_TAGS[*]}"
RESTIC_CMD+=" backup $BACKUP_SOURCE"
RESTIC_CMD+=" --verbose"

# ### RUN RESTIC BACKUP #####################################
echo "🚀 Running Restic backup..."
run_or_echo "$DRY_RUN" "$RESTIC_CMD"

# ### Remount Back #####################################
if [ "$REMOUNT_AS_RO" = true ]; then
    remount_as_read_write "$DRY_RUN" "$BACKUP_SOURCE"
fi

echo "✅ Backup completed (or would have, in dry-run mode)."
