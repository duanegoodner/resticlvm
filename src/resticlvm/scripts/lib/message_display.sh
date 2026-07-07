#!/bin/bash

# Provides functions to display configuration information, backup summaries,
# and dry-run warnings for ResticLVM backup operations.
#
# Usage:
#   Intended to be sourced by backup scripts within the ResticLVM tool.
#
# Exit codes:
#   N/A (display functions only).

# Display a list of variables and their values with a title.
display_config() {
    local title="$1"
    shift
    local vars=("$@")

    echo ""
    echo "🧾 $title"
    for var in "${vars[@]}"; do
        printf "  %-22s %s\n" "$(prettify_var_name "$var"):" "${!var}"
    done
}

# Display a preformatted standard LVM snapshot backup configuration.
display_config_lvm() {
    display_config "LVM Snapshot Backup Configuration" \
        VG_NAME LV_NAME SNAPSHOT_SIZE SNAP_NAME SNAPSHOT_MOUNT_POINT \
        RESTIC_REPO RESTIC_PASSWORD_FILE EXCLUDE_PATHS BACKUP_SOURCE_PATH DRY_RUN
}

# Prettify variable names for display (underscores → dashes, capitalize).
prettify_var_name() {
    local var_name="$1"
    var_name="${var_name//_/-}"                                 # Replace underscores with dashes
    var_name="$(echo "$var_name" | tr '[:lower:]' '[:upper:]')" # Capitalize (optional)
    echo "$var_name"
}

# Display a hardcoded snapshot backup configuration summary.
display_snapshot_backup_config() {
    echo ""
    echo "🧾 LVM Snapshot Backup Configuration:"
    echo "  Volume group:          $VG_NAME"
    echo "  Logical volume:        $LV_NAME"
    echo "  Snapshot size:         $SNAPSHOT_SIZE"
    echo "  Snapshot name:         $SNAP_NAME"
    echo "  Mount point:           $SNAPSHOT_MOUNT_POINT"
    echo "  Restic repo:           $RESTIC_REPO"
    echo "  Password file:         $RESTIC_PASSWORD_FILE"
    echo "  Exclude paths:         $EXCLUDE_PATHS"
    echo "  Backup source:         $BACKUP_SOURCE_PATH"
    echo "  Dry run:               $DRY_RUN"
}

# Show a dry-run mode warning message if applicable.
display_dry_run_message() {
    local dry_run="$1"
    if [ "$dry_run" = true ]; then
        echo -e "\n🟡 The following describes what *would* happen if this were a real backup run.\n"
    fi
}

# Report per-repository backup outcomes for a single job (issue #46). Every
# repository is attempted regardless of individual failures; this prints the
# summary and returns 0 only if all succeeded, 1 if any failed — so the caller
# can exit non-zero (marking the job failed) while still having backed up to the
# working destinations.
#   $1        total repository count
#   $2..$N    repo_path of each failed repository (may be none)
report_repo_outcomes() {
    local total="$1"
    shift
    local failed=("$@")
    local nfail=${#failed[@]}
    local nok=$((total - nfail))

    echo ""
    if [ "$nfail" -eq 0 ]; then
        echo "✅ Backup completed for all ${total} repository(ies) (or would have, in dry-run mode)."
        return 0
    fi

    echo "❌ Backup finished with failures: ${nok}/${total} repository(ies) succeeded, ${nfail} failed:"
    printf '   ✗ %s\n' "${failed[@]}"
    return 1
}
