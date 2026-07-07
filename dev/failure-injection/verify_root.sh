#!/bin/bash
# Failure-injection verification — ROOT path (lv_root, chroot binds). Run as root.
#   sudo bash verify_root.sh "$(command -v rlvm)"
#
# Env overrides (defaults suit the dev VM):
#   VG=vg0  LV=lv_root  REPO=/srv/backup/root-local
#   PW=/etc/resticlvm/restic-password.txt
# Prereqs: the LV is mounted at / and REPO is an initialized restic repo.
set -uo pipefail

RLVM="${1:-${RLVM:-}}"
# shellcheck disable=SC1091
source "$(dirname "$0")/_common.sh"
fi_require_rlvm

: "${LV:=lv_root}"
: "${REPO:=/srv/backup/root-local}"

fi_clean_stale_tmp

GOOD="$FI_WORKDIR/good.toml"
BADPASS="$FI_WORKDIR/badpass.toml"
BADREPO="$FI_WORKDIR/badrepo.toml"
WRONGPW="$FI_WORKDIR/wrong-password.txt"

{
    fi_prune_block
    cat <<EOF

[volume.root]
volume_type = "lv_root"
vg_name = "$VG"
lv_name = "$LV"
snapshot_size = "2G"
backup_source_path = "/"
exclude_paths = ["/dev", "/proc", "/sys", "/tmp", "$(dirname "$REPO")"]

[[volume.root.repositories]]
repo_path = "$REPO"
password_file = "$PW"
prune_policy = "standard"
EOF
} > "$GOOD"

echo 'definitely-the-wrong-password' > "$WRONGPW"
sed "s#password_file = \"$PW\"#password_file = \"$WRONGPW\"#" "$GOOD" > "$BADPASS"
sed "s#repo_path = \"$REPO\"#repo_path = \"$(dirname "$REPO")/does-not-exist\"#" "$GOOD" > "$BADREPO"

# 1: restic fails mid-run (wrong password) — fails AFTER all binds are set up
"$RLVM" backup --config "$BADPASS" >/dev/null 2>&1
check_clean "restic fails mid-run (wrong password)" "$?"

# 2: bind step fails (nonexistent local repo → mount --bind fails)
"$RLVM" backup --config "$BADREPO" >/dev/null 2>&1
check_clean "bind step fails (nonexistent repo)" "$?"

# 3: kill restic mid-backup (SIGKILL, exact process name)
"$RLVM" backup --config "$GOOD" >/dev/null 2>&1 &
BPID=$!
if wait_for_restic 200; then sleep 0.3; pkill -9 -x restic 2>/dev/null; fi
wait "$BPID"; check_clean "kill restic mid-backup (SIGKILL)" "$?"

# 4: SIGTERM to the backup script mid-run (arm trap, then unblock restic)
"$RLVM" backup --config "$GOOD" >/dev/null 2>&1 &
BPID=$!
if wait_for_restic 200; then sleep 0.3; pkill -TERM -f 'backup_lv_root\.sh' 2>/dev/null; sleep 0.2; pkill -9 -x restic 2>/dev/null; fi
wait "$BPID"; check_clean "SIGTERM to backup script mid-run" "$?"

# 5: SIGINT (Ctrl-C emulation) to the backup script mid-run
"$RLVM" backup --config "$GOOD" >/dev/null 2>&1 &
BPID=$!
if wait_for_restic 200; then sleep 0.3; pkill -INT -f 'backup_lv_root\.sh' 2>/dev/null; sleep 0.2; pkill -9 -x restic 2>/dev/null; fi
wait "$BPID"; check_clean "SIGINT (Ctrl-C) to backup script mid-run" "$?"

echo "(control run should still SUCCEED cleanly:  sudo $RLVM backup --config $GOOD )"
fi_summary "Root-path failure-injection"
