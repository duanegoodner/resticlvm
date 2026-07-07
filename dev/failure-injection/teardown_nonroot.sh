#!/bin/bash
# Remove the disposable nonroot test volume + repo created by setup_nonroot.sh.
# Run as root. Env overrides must match setup_nonroot.sh.
set -uo pipefail

: "${VG:=vg0}"
: "${LV:=lv_testdata}"
: "${MNT:=/mnt/testdata}"
: "${REPO:=/srv/backup/testdata-local}"

# sweep any leftover snapshot of the test LV first
lvs --noheadings -o lv_name "$VG" 2>/dev/null | grep '_snapshot_' \
    | xargs -r -n1 -I{} lvremove -f "/dev/$VG/{}" 2>/dev/null || true

umount "$MNT" 2>/dev/null || true
lvremove -f "/dev/$VG/$LV" 2>/dev/null || true
rmdir "$MNT" 2>/dev/null || true
rm -rf "$REPO" 2>/dev/null || true
echo "✅ Nonroot test volume/repo removed."
