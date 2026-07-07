#!/bin/bash
# Failure-injection verification — NONROOT path (lv_nonroot, no chroot). Run as
# root, after setup_nonroot.sh.
#   sudo bash verify_nonroot.sh "$(command -v rlvm)"
#
# Env overrides must match setup_nonroot.sh:
#   VG=vg0  LV=lv_testdata  MNT=/mnt/testdata  REPO=/srv/backup/testdata-local
set -uo pipefail

RLVM="${1:-${RLVM:-}}"
# shellcheck disable=SC1091
source "$(dirname "$0")/_common.sh"
fi_require_rlvm

: "${LV:=lv_testdata}"
: "${MNT:=/mnt/testdata}"
: "${REPO:=/srv/backup/testdata-local}"

fi_clean_stale_tmp

GOOD="$FI_WORKDIR/good_nonroot.toml"
BADPASS="$FI_WORKDIR/badpass_nonroot.toml"
WRONGPW="$FI_WORKDIR/wrong-password.txt"

{
    fi_prune_block
    cat <<EOF

[volume.testdata]
volume_type = "lv_nonroot"
vg_name = "$VG"
lv_name = "$LV"
snapshot_size = "512M"
backup_source_path = "$MNT"
exclude_paths = []

[[volume.testdata.repositories]]
repo_path = "$REPO"
password_file = "$PW"
prune_policy = "standard"
EOF
} > "$GOOD"

echo 'definitely-the-wrong-password' > "$WRONGPW"
sed "s#password_file = \"$PW\"#password_file = \"$WRONGPW\"#" "$GOOD" > "$BADPASS"

# 1: restic fails mid-run (wrong password)
"$RLVM" backup --config "$BADPASS" >/dev/null 2>&1
check_clean "restic fails mid-run (wrong password)" "$?"

# 2: kill restic mid-backup (SIGKILL, exact process name)
"$RLVM" backup --config "$GOOD" >/dev/null 2>&1 &
BPID=$!
if wait_for_restic 200; then sleep 0.3; pkill -9 -x restic 2>/dev/null; fi
wait "$BPID"; check_clean "kill restic mid-backup (SIGKILL)" "$?"

# 3: SIGTERM to the nonroot backup script mid-run
"$RLVM" backup --config "$GOOD" >/dev/null 2>&1 &
BPID=$!
if wait_for_restic 200; then sleep 0.3; pkill -TERM -f 'backup_lv_nonroot\.sh' 2>/dev/null; sleep 0.2; pkill -9 -x restic 2>/dev/null; fi
wait "$BPID"; check_clean "SIGTERM to nonroot backup script" "$?"

echo "(control run should still SUCCEED cleanly:  sudo $RLVM backup --config $GOOD )"
fi_summary "Nonroot-path failure-injection"
