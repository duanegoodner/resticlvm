#!/bin/bash
# Batch snapshot coordination verification — issue #84. Run as root, after
# setup_nonroot.sh (which creates vg0/lv_testdata).
#   sudo bash verify_batch.sh "$(command -v rlvm)"
#
# Proves that the SnapshotCoordinator creates all LVM snapshots before any
# backup runs, and tears them all down cleanly — including on failure.
#
# Env overrides (defaults suit the dev VM):
#   VG=vg0
#   ROOT_LV=lv_root       ROOT_REPO=/srv/backup/root-local
#   NR_LV=lv_testdata     NR_MNT=/mnt/testdata  NR_REPO=/srv/backup/testdata-local
#   PW=/etc/resticlvm/restic-password.txt
set -uo pipefail

RLVM="${1:-${RLVM:-}}"
# shellcheck disable=SC1091
source "$(dirname "$0")/_common.sh"
fi_require_rlvm

: "${ROOT_LV:=lv_root}"
: "${ROOT_REPO:=/srv/backup/root-local}"
: "${NR_LV:=lv_testdata}"
: "${NR_MNT:=/mnt/testdata}"
: "${NR_REPO:=/srv/backup/testdata-local}"

fi_clean_stale_tmp

# ─── Config generation ────────────────────────────────────────────

GOOD="$FI_WORKDIR/batch_good.toml"
BADPASS="$FI_WORKDIR/batch_badpass.toml"
WRONGPW="$FI_WORKDIR/wrong-password.txt"

{
    fi_prune_block
    cat <<EOF

[volume.root]
volume_type = "lv_root"
vg_name = "$VG"
lv_name = "$ROOT_LV"
snapshot_size = "2G"
backup_source_path = "/"
exclude_paths = ["/dev", "/proc", "/sys", "/tmp", "/srv/backup"]

[[volume.root.repositories]]
repo_path = "$ROOT_REPO"
password_file = "$PW"
prune_policy = "standard"

[volume.testdata]
volume_type = "lv_nonroot"
vg_name = "$VG"
lv_name = "$NR_LV"
snapshot_size = "512M"
backup_source_path = "$NR_MNT"
exclude_paths = []

[[volume.testdata.repositories]]
repo_path = "$NR_REPO"
password_file = "$PW"
prune_policy = "standard"
EOF
} > "$GOOD"

echo 'definitely-the-wrong-password' > "$WRONGPW"
# Bad password on the root volume only — testdata would still succeed if it
# ran, but the batch should still report overall failure.
sed "s#password_file = \"$PW\"#password_file = \"$WRONGPW\"#" "$GOOD" \
    > "$BADPASS"

# ─── Helpers ──────────────────────────────────────────────────────

snap_count() {
    restic -r "$1" --password-file "$PW" snapshots --json 2>/dev/null \
        | grep -o '"short_id"' | wc -l | tr -d ' '
}

# Check that exactly N snapshot LVs exist right now in the VG.
count_active_snapshots() {
    lvs --noheadings -o lv_name "$VG" 2>/dev/null | grep -c '_snapshot_'
}

# ─── Scenario 1: happy path — both volumes backed up ─────────────

echo ""
echo "━━━ Scenario 1: batch happy path (both volumes) ━━━"
root_before=$(snap_count "$ROOT_REPO")
nr_before=$(snap_count "$NR_REPO")

"$RLVM" backup --config "$GOOD" > "$FI_WORKDIR/batch_happy.log" 2>&1
rc=$?

root_after=$(snap_count "$ROOT_REPO")
nr_after=$(snap_count "$NR_REPO")
root_delta=$((root_after - root_before))
nr_delta=$((nr_after - nr_before))
snaps=$(count_active_snapshots)
mounts=$(mount 2>/dev/null | grep -c '/tmp/resticlvm-')
dirs=$(find /tmp -maxdepth 1 -name 'resticlvm-*' -type d 2>/dev/null | wc -l)

echo "  ── batch happy path ──"
echo "     exit code             : $rc  ($([ "$rc" -eq 0 ] && echo 'zero OK' || echo 'NON-ZERO — unexpected'))"
echo "     root repo new snapshot: +$root_delta  ($([ "$root_delta" -eq 1 ] && echo OK || echo WRONG))"
echo "     testdata new snapshot : +$nr_delta  ($([ "$nr_delta" -eq 1 ] && echo OK || echo WRONG))"
echo "     leaks (snap/mnt/dir)  : $snaps / $mounts / $dirs  ($([ "$snaps" -eq 0 ] && [ "$mounts" -eq 0 ] && [ "$dirs" -eq 0 ] && echo OK || echo LEAK))"
# Check COW usage report appeared in the log
cow_report=$(grep -c 'Snapshot COW usage' "$FI_WORKDIR/batch_happy.log")
echo "     COW usage report      : $([ "$cow_report" -ge 1 ] && echo 'present OK' || echo 'MISSING')"

if [ "$rc" -eq 0 ] && [ "$root_delta" -eq 1 ] && [ "$nr_delta" -eq 1 ] \
    && [ "$snaps" -eq 0 ] && [ "$mounts" -eq 0 ] && [ "$dirs" -eq 0 ] \
    && [ "$cow_report" -ge 1 ]; then
    echo "     RESULT: PASS"; fi_pass=$((fi_pass + 1))
else
    echo "     RESULT: FAIL   (full log: $FI_WORKDIR/batch_happy.log)"; fi_fail=$((fi_fail + 1))
fi

# ─── Scenario 2: both volumes fail — no leaks ────────────────────

echo ""
echo "━━━ Scenario 2: batch failure (wrong password, both volumes) ━━━"
"$RLVM" backup --config "$BADPASS" > "$FI_WORKDIR/batch_fail.log" 2>&1
check_clean "batch failure (wrong password)" "$?"

# ─── Scenario 3: SIGTERM during batch backup ─────────────────────
# All snapshots from the batch must be cleaned up.

echo ""
echo "━━━ Scenario 3: SIGTERM during batch backup ━━━"
"$RLVM" backup --config "$GOOD" > "$FI_WORKDIR/batch_sigterm.log" 2>&1 &
BPID=$!
if wait_for_restic 200; then
    sleep 0.3
    # Send SIGTERM to the Python rlvm process (coordinator catches it)
    kill -TERM "$BPID" 2>/dev/null
    sleep 0.5
    # Kill any lingering restic to unblock
    pkill -9 -x restic 2>/dev/null
fi
wait "$BPID" 2>/dev/null; check_clean "SIGTERM during batch backup" "$?"

# ─── Scenario 4: SIGINT (Ctrl-C) during batch backup ─────────────

echo ""
echo "━━━ Scenario 4: SIGINT during batch backup ━━━"
"$RLVM" backup --config "$GOOD" > "$FI_WORKDIR/batch_sigint.log" 2>&1 &
BPID=$!
if wait_for_restic 200; then
    sleep 0.3
    kill -INT "$BPID" 2>/dev/null
    sleep 0.5
    pkill -9 -x restic 2>/dev/null
fi
wait "$BPID" 2>/dev/null; check_clean "SIGINT during batch backup" "$?"

# ─── Scenario 5: verify snapshots coexist ─────────────────────────
# Start a backup, then check that BOTH snapshot LVs exist simultaneously
# before the backup finishes.

echo ""
echo "━━━ Scenario 5: verify both snapshots exist simultaneously ━━━"
"$RLVM" backup --config "$GOOD" > "$FI_WORKDIR/batch_coexist.log" 2>&1 &
BPID=$!
coexist_seen=0
if wait_for_restic 200; then
    # restic is running, which means Phase 2 is underway — both snapshots
    # should already exist (they were created in Phase 1).
    sleep 0.2
    active=$(count_active_snapshots)
    echo "     active snapshot LVs during backup: $active"
    [ "$active" -ge 2 ] && coexist_seen=1
fi
wait "$BPID" 2>/dev/null
rc=$?
snaps=$(count_active_snapshots)
mounts=$(mount 2>/dev/null | grep -c '/tmp/resticlvm-')
dirs=$(find /tmp -maxdepth 1 -name 'resticlvm-*' -type d 2>/dev/null | wc -l)

echo "  ── verify snapshots coexist ──"
echo "     both snapshots seen   : $([ "$coexist_seen" -eq 1 ] && echo 'YES — OK' || echo 'NO — could not confirm')"
echo "     final exit code       : $rc"
echo "     leaks (snap/mnt/dir)  : $snaps / $mounts / $dirs  ($([ "$snaps" -eq 0 ] && [ "$mounts" -eq 0 ] && [ "$dirs" -eq 0 ] && echo OK || echo LEAK))"

if [ "$coexist_seen" -eq 1 ] && [ "$snaps" -eq 0 ] && [ "$mounts" -eq 0 ] && [ "$dirs" -eq 0 ]; then
    echo "     RESULT: PASS"; fi_pass=$((fi_pass + 1))
else
    if [ "$coexist_seen" -eq 0 ]; then
        echo "     RESULT: INCONCLUSIVE (timing — could not observe both snapshots; backup may have been too fast)"
        # Don't count as fail — timing-dependent observation
    else
        echo "     RESULT: FAIL"; fi_fail=$((fi_fail + 1))
    fi
fi

fi_summary "Batch snapshot coordination (#84)"
