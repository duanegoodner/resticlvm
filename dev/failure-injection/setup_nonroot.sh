#!/bin/bash
# Create a disposable non-root LVM volume for nonroot failure-injection. Run as
# root. Remove afterward with teardown_nonroot.sh.
#
# Env overrides (defaults suit the dev VM):
#   VG=vg0  LV=lv_testdata  MNT=/mnt/testdata
#   REPO=/srv/backup/testdata-local  PW=/etc/resticlvm/restic-password.txt
# Requires free extents in $VG (for the LV + its snapshot at verify time).
set -euo pipefail

: "${VG:=vg0}"
: "${LV:=lv_testdata}"
: "${MNT:=/mnt/testdata}"
: "${REPO:=/srv/backup/testdata-local}"
: "${PW:=/etc/resticlvm/restic-password.txt}"

echo "📦 Creating ${VG}/${LV} (1G) ..."
lvcreate -y -L 1G -n "$LV" "$VG"
mkfs.ext4 -q "/dev/$VG/$LV"
mkdir -p "$MNT"
mount "/dev/$VG/$LV" "$MNT"

echo "🧾 Writing ~200 MiB of payload so restic runs long enough to interrupt ..."
mkdir -p "$MNT/payload"
dd if=/dev/urandom of="$MNT/payload/blob" bs=1M count=200 status=none
for i in $(seq 1 200); do head -c 4096 /dev/urandom > "$MNT/payload/f_$i"; done
sync

echo "🔐 Initializing restic repo $REPO ..."
if ! restic -r "$REPO" --password-file "$PW" cat config >/dev/null 2>&1; then
    restic -r "$REPO" --password-file "$PW" init
else
    echo "   (repo already exists — reusing)"
fi

echo "✅ Nonroot test volume ready: $VG/$LV mounted at $MNT, repo at $REPO"
