#!/bin/bash
# Shared helpers for the resticlvm failure-injection harness (issue #24).
# Sourced by verify_root.sh / verify_nonroot.sh — not run directly.
#
# These scripts prove that a mid-run failure leaves NO leaked LVM snapshot,
# NO leftover bind/snapshot mount, and NO stray temp dir, and that rlvm still
# exits non-zero. See docs/FAILURE_INJECTION_TESTING.md for the full runbook.

# rlvm entrypoint. sudo scrubs PATH, so the verify scripts take it as $1 (or set
# RLVM). Pin the absolute path, e.g. RLVM="$(command -v rlvm)".
: "${RLVM:=}"

# Environment defaults — override via env vars to match your VM/setup.
: "${VG:=vg0}"                                  # volume group holding the LV
: "${PW:=/etc/resticlvm/restic-password.txt}"   # restic password file

# Scratch dir for generated configs. NOTE: deliberately NOT under a
# /tmp/resticlvm-* path, so it can never be mistaken for a leaked snapshot dir.
# Kept after the run so the printed control-run command still works; prior
# workdirs are swept here on each start.
rm -rf "${TMPDIR:-/tmp}"/rlvm-fi.* 2>/dev/null || true
# shellcheck disable=SC2034  # consumed by the scripts that source this file
FI_WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/rlvm-fi.XXXXXX")"

fi_pass=0
fi_fail=0

# Emit a [prune_policy.standard] block usable by any generated config.
fi_prune_block() {
    cat <<'EOF'
[prune_policy.standard]
keep_last = 10
keep_daily = 7
keep_weekly = 4
keep_monthly = 6
keep_yearly = 1
EOF
}

# Remove stale, always-empty /tmp/resticlvm-* dirs from earlier runs so leak
# counts reflect only the current run.
fi_clean_stale_tmp() {
    local n
    n=$(find /tmp -maxdepth 1 -name 'resticlvm-*' -type d 2>/dev/null | wc -l)
    if [ "$n" -gt 0 ]; then
        echo "ℹ️  Removing $n stale /tmp/resticlvm-* dir(s) before starting."
        rm -rf /tmp/resticlvm-* 2>/dev/null || true
    fi
}

# Wait until a process literally named "restic" is running (so injection hits
# an in-progress backup). $1 = timeout in deciseconds (default 200 = 20s).
wait_for_restic() {
    local i=0
    while ! pgrep -x restic >/dev/null 2>&1; do
        i=$((i + 1))
        [ "$i" -ge "${1:-200}" ] && return 1
        sleep 0.1
    done
}

# Assert clean teardown. $1 = scenario name, $2 = observed rlvm exit code.
# IMPORTANT: kill restic by exact name (pkill -x restic), never `pkill -f
# restic`: the backup script's own cmdline contains "restic-password.txt" and
# the repo path, so an -f pattern would SIGKILL the (untrappable) script and
# manufacture a false leak.
check_clean() {
    local name="$1" rc="$2" snaps mounts dirs
    snaps=$(lvs --noheadings -o lv_name "$VG" 2>/dev/null | grep -c '_snapshot_')
    mounts=$(mount 2>/dev/null | grep -c '/tmp/resticlvm-')
    dirs=$(find /tmp -maxdepth 1 -name 'resticlvm-*' -type d 2>/dev/null | wc -l)
    echo "  ── $name ──"
    echo "     rlvm exit code  : $rc  ($([ "$rc" -ne 0 ] && echo non-zero OK || echo 'ZERO — unexpected'))"
    echo "     snapshot LVs    : $snaps  ($([ "$snaps" -eq 0 ] && echo OK || echo LEAK))"
    echo "     resticlvm mounts: $mounts  ($([ "$mounts" -eq 0 ] && echo OK || echo LEAK))"
    echo "     temp dirs       : $dirs  ($([ "$dirs" -eq 0 ] && echo OK || echo LEAK))"
    [ "$dirs" -ne 0 ] && find /tmp -maxdepth 1 -name 'resticlvm-*' -type d 2>/dev/null | sed 's/^/       /'
    if [ "$rc" -ne 0 ] && [ "$snaps" -eq 0 ] && [ "$mounts" -eq 0 ] && [ "$dirs" -eq 0 ]; then
        echo "     RESULT: PASS"
        fi_pass=$((fi_pass + 1))
    else
        echo "     RESULT: FAIL"
        fi_fail=$((fi_fail + 1))
        # best-effort manual cleanup so the next scenario starts clean
        mount | awk '/\/tmp\/resticlvm-/ {print $3}' | sort -r | xargs -r -n1 umount -l 2>/dev/null
        lvs --noheadings -o lv_name "$VG" 2>/dev/null | grep '_snapshot_' \
            | xargs -r -n1 -I{} lvremove -f "/dev/$VG/{}" 2>/dev/null
        rm -rf /tmp/resticlvm-* 2>/dev/null
    fi
}

fi_summary() {
    echo
    echo "════════ $1: $fi_pass passed, $fi_fail failed ════════"
    [ "$fi_fail" -eq 0 ]
}

fi_require_rlvm() {
    if [ -z "$RLVM" ]; then
        echo "❌ Pass the rlvm path as the first argument (sudo scrubs PATH):" >&2
        echo "   sudo bash $0 \"\$(command -v rlvm)\"" >&2
        exit 2
    fi
    if [ "$(id -u)" -ne 0 ]; then
        echo "❌ Must run as root (LVM snapshot + chroot)." >&2
        exit 2
    fi
}
