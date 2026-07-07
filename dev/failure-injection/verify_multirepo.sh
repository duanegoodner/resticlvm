#!/bin/bash
# Multi-repo resilience verification — issue #46. Run as root.
#   sudo bash verify_multirepo.sh "$(command -v rlvm)"
#
# Proves that within one lv_root job a failing repository does NOT block the
# others: whichever position the bad repo takes, the good repo still gets a new
# snapshot, the job exits non-zero, #24 cleanup still holds, and the controlled
# exit prints no "aborted" trap message.
#
# Env overrides (defaults suit the dev VM):
#   VG=vg0  LV=lv_root  GOOD_REPO=/srv/backup/root-local  BAD_REPO=/srv/backup/root-bad
#   PW=/etc/resticlvm/restic-password.txt
set -uo pipefail

RLVM="${1:-${RLVM:-}}"
# shellcheck disable=SC1091
source "$(dirname "$0")/_common.sh"
fi_require_rlvm

: "${LV:=lv_root}"
: "${GOOD_REPO:=/srv/backup/root-local}"
: "${BAD_REPO:=/srv/backup/root-bad}"

# The wrong-password file must live inside the root snapshot/chroot (not in
# /tmp), so the bad repo fails on a genuine wrong password rather than a missing
# file.
WRONGPW=/etc/resticlvm/wrong-password.txt
echo 'the-wrong-password' > "$WRONGPW"
trap 'rm -f "$WRONGPW" 2>/dev/null || true' EXIT

fi_clean_stale_tmp

# Ensure the "bad" repo exists, initialized with the CORRECT password (the
# failure is purely the wrong password referenced in the config).
restic -r "$BAD_REPO" --password-file "$PW" cat config >/dev/null 2>&1 \
    || restic -r "$BAD_REPO" --password-file "$PW" init >/dev/null 2>&1

prune_block() { printf '[prune_policy.standard]\nkeep_last = 10\nkeep_daily = 7\nkeep_weekly = 4\nkeep_monthly = 6\nkeep_yearly = 1\n'; }
vol_head()    { printf '\n[volume.root]\nvolume_type = "lv_root"\nvg_name = "%s"\nlv_name = "%s"\nsnapshot_size = "2G"\nbackup_source_path = "/"\nexclude_paths = ["/dev","/proc","/sys","/tmp","/srv/backup"]\n' "$VG" "$LV"; }
repo_block()  { printf '\n[[volume.root.repositories]]\nrepo_path = "%s"\npassword_file = "%s"\nprune_policy = "standard"\n' "$1" "$2"; }

# Count snapshots robustly: restic --json prints the array on one line, so count
# occurrences (grep -o), not matching lines (grep -c).
snap_count() { restic -r "$1" --password-file "$PW" snapshots --json 2>/dev/null | grep -o '"short_id"' | wc -l | tr -d ' '; }

run_case() { # $1 = case name, $2 = config path
    local name="$1" cfg="$2" before after rc log good_delta snaps mounts dirs
    log="$FI_WORKDIR/${name}.log"
    before=$(snap_count "$GOOD_REPO")
    "$RLVM" backup --config "$cfg" >"$log" 2>&1; rc=$?
    after=$(snap_count "$GOOD_REPO")
    good_delta=$((after - before))
    snaps=$(lvs --noheadings -o lv_name "$VG" 2>/dev/null | grep -c '_snapshot_')
    mounts=$(mount 2>/dev/null | grep -c '/tmp/resticlvm-')
    dirs=$(find /tmp -maxdepth 1 -name 'resticlvm-*' -type d 2>/dev/null | wc -l)

    echo "  ── $name ──"
    echo "     exit code             : $rc  ($([ "$rc" -ne 0 ] && echo 'non-zero OK' || echo 'ZERO — unexpected'))"
    echo "     good repo new snapshot: +$good_delta  ($([ "$good_delta" -eq 1 ] && echo OK || echo 'WRONG — good repo not backed up!'))"
    echo "     summary line          : $(grep -oE '[0-9]+/[0-9]+ repository\(ies\) succeeded, [0-9]+ failed' "$log" | tail -1)"
    echo "     leaks (snap/mnt/dir)  : $snaps / $mounts / $dirs  ($([ "$snaps" -eq 0 ] && [ "$mounts" -eq 0 ] && [ "$dirs" -eq 0 ] && echo OK || echo LEAK))"
    echo "     no 'aborted' trap msg : $(grep -q 'Backup aborted' "$log" && echo 'NO — unexpected' || echo OK)"

    if [ "$rc" -ne 0 ] && [ "$good_delta" -eq 1 ] && [ "$snaps" -eq 0 ] && [ "$mounts" -eq 0 ] && [ "$dirs" -eq 0 ] \
       && ! grep -q 'Backup aborted' "$log"; then
        echo "     RESULT: PASS"; fi_pass=$((fi_pass + 1))
    else
        echo "     RESULT: FAIL   (full log: $log)"; fi_fail=$((fi_fail + 1))
        mount | awk '/\/tmp\/resticlvm-/ {print $3}' | sort -r | xargs -r -n1 umount -l 2>/dev/null
        lvs --noheadings -o lv_name "$VG" 2>/dev/null | grep '_snapshot_' | xargs -r -n1 -I{} lvremove -f "/dev/$VG/{}" 2>/dev/null
        rm -rf /tmp/resticlvm-* 2>/dev/null
    fi
}

# Bad repo FIRST — the pre-#46 failure mode (early failure blocked the good repo).
{ prune_block; vol_head; repo_block "$BAD_REPO" "$WRONGPW"; repo_block "$GOOD_REPO" "$PW"; } > "$FI_WORKDIR/bad_first.toml"
run_case "bad-first_good-second" "$FI_WORKDIR/bad_first.toml"

# Bad repo SECOND — good backs up, then the bad one fails.
{ prune_block; vol_head; repo_block "$GOOD_REPO" "$PW"; repo_block "$BAD_REPO" "$WRONGPW"; } > "$FI_WORKDIR/good_first.toml"
run_case "good-first_bad-second" "$FI_WORKDIR/good_first.toml"

fi_summary "Multi-repo resilience (#46)"
