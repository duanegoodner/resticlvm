#!/bin/bash

# Create and mount a single LVM snapshot for batch snapshot coordination.
#
# This script is the "create" half of the snapshot lifecycle, intended to be
# called by the Python SnapshotCoordinator. It does NOT install a cleanup
# trap — the coordinator owns lifecycle management across all snapshots.
#
# Arguments:
#   -g  Volume group name.
#   -l  Logical volume name.
#   -z  Snapshot size (e.g., "5G").
#   -t  (Optional) Batch timestamp (YYYYmmdd_HHMMSS). If omitted, generates one.
#   -n  (Optional) Dry-run mode.
#
# Output (stdout, machine-parseable):
#   SNAPSHOT_DEVICE=/dev/VG/SNAP_NAME
#   SNAPSHOT_MOUNT_POINT=/tmp/resticlvm-TIMESTAMP/SNAP_NAME
#   MOUNT_BASE=/tmp/resticlvm-TIMESTAMP
#   SNAP_NAME=vg_lv_snapshot_TIMESTAMP
#
# Exit codes:
#   0  Success
#   1  Any fatal error

set -euo pipefail

SCRIPT_DIR="$(dirname "$0")"

# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/command_runners.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/lv_snapshots.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/pre_checks.sh"

# ─── Require Running as Root ─────────────────────────────────────
root_check

# ─── Parse Arguments ─────────────────────────────────────────────
VG_NAME=""
LV_NAME=""
SNAPSHOT_SIZE=""
BATCH_TIMESTAMP=""
DRY_RUN=false

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
        SNAPSHOT_SIZE="$2"
        shift 2
        ;;
    -t | --timestamp)
        BATCH_TIMESTAMP="$2"
        shift 2
        ;;
    -n | --dry-run)
        DRY_RUN=true
        shift
        ;;
    *)
        echo "❌ Unknown option: $1" >&2
        echo "Usage: $0 -g VG -l LV -z SIZE [-t TIMESTAMP] [-n]" >&2
        exit 1
        ;;
    esac
done

# ─── Validate ─────────────────────────────────────────────────────
if [[ -z "$VG_NAME" || -z "$LV_NAME" || -z "$SNAPSHOT_SIZE" ]]; then
    echo "❌ Error: -g, -l, and -z are required" >&2
    echo "Usage: $0 -g VG -l LV -z SIZE [-t TIMESTAMP] [-n]" >&2
    exit 1
fi

# ─── Derived Variables ───────────────────────────────────────────
if [[ -n "$BATCH_TIMESTAMP" ]]; then
    SNAP_NAME="${VG_NAME}_${LV_NAME}_snapshot_${BATCH_TIMESTAMP}"
    MOUNT_BASE="/tmp/resticlvm-${BATCH_TIMESTAMP}"
else
    SNAP_NAME=$(generate_snapshot_name "$VG_NAME" "$LV_NAME")
    MOUNT_BASE=$(generate_mount_base)
fi

LV_DEVICE_PATH="/dev/$VG_NAME/$LV_NAME"
SNAPSHOT_MOUNT_POINT="${MOUNT_BASE}/${SNAP_NAME}"

# ─── Pre-checks ───────────────────────────────────────────────────
check_device_path "$LV_DEVICE_PATH"
confirm_not_yet_exist_snapshot_mount_point "$SNAPSHOT_MOUNT_POINT"

# ─── Create and Mount ────────────────────────────────────────────
create_snapshot "$DRY_RUN" "$SNAPSHOT_SIZE" "$SNAP_NAME" "$VG_NAME" "$LV_NAME"
mount_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"

# ─── Output (machine-parseable) ──────────────────────────────────
echo "SNAPSHOT_DEVICE=$LV_DEVICE_PATH"
echo "SNAPSHOT_MOUNT_POINT=$SNAPSHOT_MOUNT_POINT"
echo "MOUNT_BASE=$MOUNT_BASE"
echo "SNAP_NAME=$SNAP_NAME"
