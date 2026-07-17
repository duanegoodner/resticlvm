#!/bin/bash

# Tear down a single LVM snapshot: unmount, remove snapshot LV, clean up dirs.
#
# This script is the "teardown" half of the snapshot lifecycle, intended to be
# called by the Python SnapshotCoordinator. It is idempotent — safe to call
# even if the snapshot has already been cleaned up.
#
# Arguments:
#   -g  Volume group name.
#   -s  Snapshot name (the LV name of the snapshot).
#   -m  Snapshot mount point.
#   -b  Mount base directory (parent of the mount point).
#   -n  (Optional) Dry-run mode.
#
# Exit codes:
#   0  Always (best-effort teardown never fails the caller)

set -uo pipefail
# Note: no -e — teardown is best-effort and must not abort on individual errors.

SCRIPT_DIR="$(dirname "$0")"

# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/command_runners.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/lv_snapshots.sh"

# ─── Parse Arguments ─────────────────────────────────────────────
VG_NAME=""
SNAP_NAME=""
SNAPSHOT_MOUNT_POINT=""
MOUNT_BASE=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
    -g | --vg-name)
        VG_NAME="$2"
        shift 2
        ;;
    -s | --snap-name)
        SNAP_NAME="$2"
        shift 2
        ;;
    -m | --mount-point)
        SNAPSHOT_MOUNT_POINT="$2"
        shift 2
        ;;
    -b | --mount-base)
        MOUNT_BASE="$2"
        shift 2
        ;;
    -n | --dry-run)
        DRY_RUN=true
        shift
        ;;
    *)
        echo "❌ Unknown option: $1" >&2
        echo "Usage: $0 -g VG -s SNAP_NAME -m MOUNT_POINT -b MOUNT_BASE [-n]" >&2
        exit 1
        ;;
    esac
done

# ─── Validate ─────────────────────────────────────────────────────
if [[ -z "$VG_NAME" || -z "$SNAP_NAME" || -z "$SNAPSHOT_MOUNT_POINT" || -z "$MOUNT_BASE" ]]; then
    echo "❌ Error: -g, -s, -m, and -b are required" >&2
    echo "Usage: $0 -g VG -s SNAP_NAME -m MOUNT_POINT -b MOUNT_BASE [-n]" >&2
    exit 1
fi

# ─── Teardown ─────────────────────────────────────────────────────
if [ "$DRY_RUN" = true ]; then
    echo -e "${DRY_RUN_PREFIX} cleanup_snapshot_resources \"$SNAPSHOT_MOUNT_POINT\" \"$MOUNT_BASE\" \"$VG_NAME\" \"$SNAP_NAME\""
else
    echo "🧹 Tearing down snapshot $SNAP_NAME..."
    cleanup_snapshot_resources "$SNAPSHOT_MOUNT_POINT" "$MOUNT_BASE" "$VG_NAME" "$SNAP_NAME"
    echo "✅ Snapshot $SNAP_NAME teardown complete."
fi
