#!/bin/bash

# Provides functions to create, mount, and clean up LVM snapshots
# for use in ResticLVM backups.
#
# Usage:
#   Intended to be sourced by backup scripts within the ResticLVM tool.
#
# Requirements:
#   - Must be run with root privileges (direct root or via sudo).
#   - LVM tools must be installed and available (lvcreate, lvremove, etc.).
#
# Exit codes:
#   Non-zero if any snapshot operation fails (unless in dry-run mode).

# Create an LVM snapshot for a given logical volume.
create_snapshot() {
    echo "📸 Creating LVM snapshot..."
    local dry_run=$1
    local snapshot_size=$2
    local snap_name=$3
    local vg_name=$4
    local lv_name=$5

    run_or_echo "$dry_run" "lvcreate --size $snapshot_size --snapshot --name $snap_name /dev/$vg_name/$lv_name"
}

# Mount an LVM snapshot read-only at a given mount point.
mount_snapshot() {
    local dry_run=$1
    local snapshot_mount_point=$2
    local vg_name=$3
    local snap_name=$4

    echo "📂 Mounting snapshot read-only..."
    run_or_echo "$dry_run" "mkdir -p \"$snapshot_mount_point\""
    run_or_echo "$dry_run" "mount /dev/$vg_name/$snap_name \"$snapshot_mount_point\" || { echo '❌ Failed to mount snapshot'; exit 1; }"
}

# Unmount and remove an LVM snapshot and its mount point.
clean_up_snapshot() {
    local dry_run="$1"
    local snapshot_mount_point="$2"
    local vg_name="$3"
    local snap_name="$4"

    echo "🧹 Cleaning up..."
    run_or_echo "$dry_run" "umount \"$snapshot_mount_point\""
    run_or_echo "$dry_run" "lvremove -y \"/dev/$vg_name/$snap_name\""
    run_or_echo "$dry_run" "rmdir \"$snapshot_mount_point\""
}

# Generate a timestamped name for an LVM snapshot.
generate_snapshot_name() {
    local vg_name="$1"
    local lv_name="$2"
    local timestamp
    timestamp=$(date +"%Y%m%d_%H%M%S")
    echo "${vg_name}_${lv_name}_snapshot_${timestamp}"
}

# Generate timestamped base directory for snapshot mounts
generate_mount_base() {
    local timestamp
    timestamp=$(date +"%Y%m%d_%H%M%S")
    echo "/tmp/resticlvm-${timestamp}"
}

# ─── Cleanup-on-failure (issue #24) ───────────────────────────────
#
# Idempotent, best-effort teardown of a snapshot and everything mounted under
# it. Safe to call when nothing (or only part) of it was created, and safe to
# call more than once. Every step is guarded and ignores its own errors, so it
# never masks the caller's exit code. Uses the discover-and-tear-down approach:
# it finds whatever is mounted under the snapshot rather than tracking binds.
cleanup_snapshot_resources() {
    local snapshot_mount_point="$1"
    local mount_base="$2"
    local vg_name="$3"
    local snap_name="$4"

    if [ -n "$snapshot_mount_point" ]; then
        # Unmount anything bound under the snapshot (chroot binds + the per-repo
        # bind), deepest path first so parents unmount last. umount -l is the
        # fallback for a still-busy target.
        local target
        while IFS= read -r target; do
            [ "$target" = "$snapshot_mount_point" ] && continue
            umount "$target" 2>/dev/null \
                || umount -l "$target" 2>/dev/null || true
        done < <(findmnt -rn -o TARGET 2>/dev/null \
            | awk -v base="$snapshot_mount_point/" 'index($0, base) == 1' \
            | awk '{ print length, $0 }' | sort -rn | cut -d' ' -f2-)

        # Unmount the snapshot itself. Prefer a real unmount (retried briefly)
        # over a lazy one: a lazy detach can leave the device transiently busy
        # and then race the lvremove below.
        if mountpoint -q "$snapshot_mount_point" 2>/dev/null; then
            local u=0
            until umount "$snapshot_mount_point" 2>/dev/null; do
                u=$((u + 1))
                if [ "$u" -ge 5 ]; then
                    umount -l "$snapshot_mount_point" 2>/dev/null || true
                    break
                fi
                sleep 0.3
            done
        fi
    fi

    # Remove the snapshot LV by its exact, timestamped name (never a glob),
    # regardless of whether the unmounts above fully succeeded. After a process
    # (e.g. restic) has read the mounted snapshot, the device can stay briefly
    # busy once unmounted, so let udev settle and retry lvremove for a few
    # seconds rather than giving up after one attempt.
    if [ -n "$vg_name" ] && [ -n "$snap_name" ] \
        && lvs "/dev/$vg_name/$snap_name" >/dev/null 2>&1; then
        command -v udevadm >/dev/null 2>&1 && udevadm settle >/dev/null 2>&1 || true
        local r=0
        while lvs "/dev/$vg_name/$snap_name" >/dev/null 2>&1; do
            lvremove -f "/dev/$vg_name/$snap_name" >/dev/null 2>&1 && break
            r=$((r + 1))
            [ "$r" -ge 10 ] && break
            sleep 0.3
        done
    fi

    # Remove the mount point, any now-empty parents, and the temp base dir.
    # Bounded at mount_base so this never climbs into /tmp or above, and rmdir
    # only removes empty dirs so a still-populated path is left untouched.
    if [ -n "$snapshot_mount_point" ] && [ -n "$mount_base" ]; then
        local dir="$snapshot_mount_point"
        while [ -n "$dir" ] && [ "$dir" != "$mount_base" ] && [ "$dir" != "/" ]; do
            rmdir "$dir" 2>/dev/null || break
            dir=$(dirname "$dir")
        done
        rmdir "$mount_base" 2>/dev/null || true
    fi
}

# EXIT/signal trap handler. Preserves the original exit code, disarms itself to
# avoid re-entry, and skips real teardown in dry-run mode. Reads the well-known
# globals set by the backup scripts (SNAPSHOT_MOUNT_POINT, MOUNT_BASE, VG_NAME,
# SNAP_NAME, DRY_RUN).
# shellcheck disable=SC2154
_snapshot_cleanup_trap() {
    local rc=$?
    trap - EXIT INT TERM HUP
    if [ "${DRY_RUN:-false}" != true ]; then
        if [ "$rc" -ne 0 ]; then
            echo "" >&2
            echo "⚠️  Backup aborted (exit $rc) — releasing LVM snapshot and mounts…" >&2
        fi
        cleanup_snapshot_resources \
            "${SNAPSHOT_MOUNT_POINT:-}" "${MOUNT_BASE:-}" \
            "${VG_NAME:-}" "${SNAP_NAME:-}"
    fi
    exit "$rc"
}

# Install the cleanup trap on every exit path (normal, error, signal). Call this
# immediately after the snapshot is created. Signal traps re-exit with a
# conventional 128+signo code, which routes through the EXIT trap so cleanup
# runs exactly once.
install_snapshot_cleanup_trap() {
    trap '_snapshot_cleanup_trap' EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    trap 'exit 129' HUP
}
