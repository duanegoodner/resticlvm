#!/bin/bash

# Set variables
VG_NAME="vg0"                                   # Volume group name
LV_NAME="lv0"                                   # Logical volume name
SNAP_NAME="lv0_snapshot"                        # Snapshot name
SNAP_SIZE="1G"                                  # Snapshot size
SNAPSHOT_MOUNT_POINT="/srv/snapshot_for_restic" # Mount point for the snapshot
RESTIC_REPO="/backup/restic/restic-root/"
RESTIC_PASSWORD_FILE="/home/duane/resticlvm/secrets/repo_password.txt" # Path to Restic password file

# Paths to exclude (space-separated list)
EXCLUDE_PATHS="/dev /media /mnt /proc /run /sys /tmp /var/tmp /var/lib/libvirt/images"

# Ensure we run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo."
    exit 1
fi

# Create snapshot of root LV
echo "Creating LVM snapshot..."
lvcreate --size $SNAP_SIZE --snapshot --name $SNAP_NAME /dev/$VG_NAME/$LV_NAME
if [ $? -ne 0 ]; then
    echo "Failed to create LVM snapshot. Exiting."
    exit 1
fi

# Mount root LV snapshot
echo "Mounting LVM snapshot..."
mkdir -p $SNAPSHOT_MOUNT_POINT
mount /dev/$VG_NAME/$SNAP_NAME $SNAPSHOT_MOUNT_POINT
if [ $? -ne 0 ]; then
    echo "Failed to mount LVM snapshot. Exiting."
    lvremove -y /dev/$VG_NAME/$SNAP_NAME
    exit 1
fi

# Bind Restic repository to snapshot environment
CHROOT_REPO_PATH="/.restic_repo"
CHROOT_REPO_FULL="$CHROOT_REPO_PATH/$(basename $RESTIC_REPO)"
mkdir -p "$SNAPSHOT_MOUNT_POINT/$CHROOT_REPO_FULL"
mount --bind "$RESTIC_REPO" "$SNAPSHOT_MOUNT_POINT/$CHROOT_REPO_FULL"

# Bind essential directories for chroot
echo "Preparing chroot environment..."
mount --bind /dev $SNAPSHOT_MOUNT_POINT/dev
mount --bind /proc $SNAPSHOT_MOUNT_POINT/proc
mount --bind /sys $SNAPSHOT_MOUNT_POINT/sys

# Convert exclude paths to a Restic-compatible string
EXCLUDE_ARGS=""
for path in $EXCLUDE_PATHS; do
    EXCLUDE_ARGS+="--exclude=$path "
done

# Enter chroot and run Restic backup
chroot "$SNAPSHOT_MOUNT_POINT" /bin/bash -c "
  export RESTIC_PASSWORD_FILE=$RESTIC_PASSWORD_FILE
  restic $EXCLUDE_ARGS -r $CHROOT_REPO_FULL backup / --verbose
"

# Exit chroot and clean up

# Unmount restic repo bind
mountpoint -q "$SNAPSHOT_MOUNT_POINT/$CHROOT_REPO_FULL" && umount "$SNAPSHOT_MOUNT_POINT/$CHROOT_REPO_FULL"

# Unmount standard chroot system paths
umount "$SNAPSHOT_MOUNT_POINT/dev"
umount "$SNAPSHOT_MOUNT_POINT/proc"
umount "$SNAPSHOT_MOUNT_POINT/sys"

# Unmount snapshot root
umount "$SNAPSHOT_MOUNT_POINT"

# Remove the snapshot
lvremove -y "/dev/$VG_NAME/$SNAP_NAME"

# Optionally clean up mount directory
rmdir "$SNAPSHOT_MOUNT_POINT"

echo "Backup completed successfully."
