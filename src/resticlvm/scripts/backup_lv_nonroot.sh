#!/bin/bash

# Backup a logical volume that is mounted somewhere other than "/" using
# Restic and LVM snapshots. Backs up directly from the mounted snapshot
# without using a chroot environment.
#
# Arguments:
#   -g  Volume group name.
#   -l  Logical volume name.
#   -z  Snapshot size (e.g., "5G").
#   -r  Path to the Restic repository.
#   -p  Path to the Restic password file.
#   -s  Path to backup source directory inside LV (e.g., "/data").
#   -e  (Optional) Comma-separated list of paths to exclude.
#   --snapshot-mount  (Optional) Path to pre-mounted snapshot (batch mode).
#   --dry-run  (Optional) Show actions without executing them.
#
# Usage:
#   This script is intended to be called internally by the ResticLVM tool.
#
# Requirements:
#   - Must be run with root privileges (direct root or via sudo).
#   - Restic must be installed and available in PATH.
#   - LVM must be installed and functional.
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
VG_NAME=""
LV_NAME=""
SNAPSHOT_SIZE=""
RESTIC_REPOS=()
RESTIC_PASSWORD_FILES=()
BACKUP_SOURCE_PATH=""
EXCLUDE_PATHS=""
DRY_RUN=false
SNAPSHOT_MOUNT=""

# ─── Parse and Validate Arguments ─────────────────────────────────
parse_arguments usage_lv_nonroot "vg-name lv-name snap-size restic-repo password-file backup-source exclude-paths snapshot-mount dry-run" "$@"

# Validate basic LVM args
validate_args usage_lv_nonroot VG_NAME LV_NAME SNAPSHOT_SIZE

# Validate repository arrays
if [ ${#RESTIC_REPOS[@]} -eq 0 ]; then
    echo "❌ Error: At least one --restic-repo is required"
    usage_lv_nonroot
fi

if [ ${#RESTIC_REPOS[@]} -ne ${#RESTIC_PASSWORD_FILES[@]} ]; then
    echo "❌ Error: Number of repos (${#RESTIC_REPOS[@]}) must match number of password files (${#RESTIC_PASSWORD_FILES[@]})"
    usage_lv_nonroot
fi

# ─── Snapshot Mode ────────────────────────────────────────────────
# When --snapshot-mount is provided, use a pre-mounted snapshot managed by the
# Python SnapshotCoordinator (batch mode, issue #84). Otherwise, create and
# manage the snapshot ourselves (standalone mode).
MANAGED_SNAPSHOT=true
if [[ -n "$SNAPSHOT_MOUNT" ]]; then
    MANAGED_SNAPSHOT=false
    SNAPSHOT_MOUNT_POINT="$SNAPSHOT_MOUNT"
fi

# ─── Derived Variables ───────────────────────────────────────────
LV_DEVICE_PATH="/dev/$VG_NAME/$LV_NAME"

# ─── Pre-checks ───────────────────────────────────────────────────
check_device_path "$LV_DEVICE_PATH"
LV_MOUNT_POINT=$(check_mount_point "$LV_DEVICE_PATH")
confirm_source_in_lv "$LV_MOUNT_POINT" "$BACKUP_SOURCE_PATH"

if [[ "$MANAGED_SNAPSHOT" == true ]]; then
    SNAP_NAME=$(generate_snapshot_name "$VG_NAME" "$LV_NAME")
    MOUNT_BASE="/tmp/resticlvm"
    SNAPSHOT_MOUNT_POINT="${MOUNT_BASE}${LV_MOUNT_POINT}"
    confirm_not_yet_exist_snapshot_mount_point "$SNAPSHOT_MOUNT_POINT"
fi

# ─── Display Configuration ───────────────────────────────────────
display_config "LVM Snapshot Backup Configuration" \
    VG_NAME LV_NAME SNAPSHOT_SIZE SNAPSHOT_MOUNT_POINT \
    EXCLUDE_PATHS BACKUP_SOURCE_PATH DRY_RUN

echo "Repositories: ${#RESTIC_REPOS[@]}"
for i in "${!RESTIC_REPOS[@]}"; do
    echo "  $((i+1)). ${RESTIC_REPOS[$i]}"
done

display_dry_run_message "$DRY_RUN"

# ─── Create and Mount Snapshot (standalone mode only) ─────────────
if [[ "$MANAGED_SNAPSHOT" == true ]]; then
    create_snapshot "$DRY_RUN" "$SNAPSHOT_SIZE" "$SNAP_NAME" "$VG_NAME" "$LV_NAME"
    # Register cleanup-on-failure as soon as the snapshot exists so any later
    # failure/signal idempotently unwinds the snapshot and its mount (issue #24).
    install_snapshot_cleanup_trap
    mount_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"
fi

# ─── Build Exclude Arguments (Once) ───────────────────────────────
EXCLUDE_ARGS=()
populate_exclude_paths EXCLUDE_ARGS "$EXCLUDE_PATHS"

RESTIC_TAGS=()
populate_restic_tags RESTIC_TAGS "$EXCLUDE_PATHS"

# ─── Loop Over Repositories ───────────────────────────────────────
echo "🚀 Backing up to ${#RESTIC_REPOS[@]} repository(ies)..."

FAILED_REPOS=()
for i in "${!RESTIC_REPOS[@]}"; do
    RESTIC_REPO="${RESTIC_REPOS[$i]}"
    RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILES[$i]}"

    echo ""
    echo "▶️  Repository $((i+1))/${#RESTIC_REPOS[@]}: $RESTIC_REPO"

    # Build Restic command. Run inside a mount namespace so we can bind-mount
    # the snapshot over the original LV mount point — restic then records the
    # real source path (e.g. /data/git) instead of the temp mount path.
    RESTIC_INNER="mount --bind $SNAPSHOT_MOUNT_POINT $LV_MOUNT_POINT"
    RESTIC_INNER+=" && restic -r $RESTIC_REPO"
    RESTIC_INNER+=" --password-file=$RESTIC_PASSWORD_FILE"
    RESTIC_INNER+=" backup $BACKUP_SOURCE_PATH"
    RESTIC_INNER+=" ${EXCLUDE_ARGS[*]}"
    RESTIC_INNER+=" ${RESTIC_TAGS[*]}"
    RESTIC_INNER+=" --verbose"

    RESTIC_CMD="unshare --mount sh -c '$RESTIC_INNER'"

    # Execute backup for this repo. A failure must not prevent the remaining
    # repositories from being attempted (issue #46).
    if run_or_echo "$DRY_RUN" "$RESTIC_CMD"; then
        echo "✅ Repository backup succeeded: $RESTIC_REPO"
    else
        echo "❌ Repository backup failed: $RESTIC_REPO"
        FAILED_REPOS+=("$RESTIC_REPO")
    fi

    # A remote repo's ssh can grab the terminal and not give it back, which would
    # suppress the next repo's restic output; restore it here (issue #72).
    restore_terminal_foreground
done

# ─── Cleanup ──────────────────────────────────────────────────────
if [[ "$MANAGED_SNAPSHOT" == true ]]; then
    clean_up_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"
    # Read by the EXIT trap (_snapshot_cleanup_trap) to distinguish an orderly exit
    # from an abort; see lib/lv_snapshots.sh.
    # shellcheck disable=SC2034
    RLVM_CLEANUP_DONE=1
fi

report_repo_outcomes "${#RESTIC_REPOS[@]}" ${FAILED_REPOS[@]+"${FAILED_REPOS[@]}"} || exit 1
