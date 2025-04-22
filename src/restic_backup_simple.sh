#!/bin/bash

# Set variables
VG_NAME="vg0"                                    # Volume group name
LV_NAME="lv0"                                              # Logical volume name
SNAP_NAME="lv0_snapshot"                                # Snapshot name
SNAP_SIZE="1G"                                             # Snapshot size
SNAPSHOT_MOUNT_POINT="/srv/snapshot_for_restic"                      # Mount point for the snapshot
RESTIC_REPO_ROOT="/backup/restic/restic-root/" 
RESTIC_REPO_BOOT="/backup/restic/restic-boot/"
RESTIC_REPO_DATE="/backup/restic/restic-data/"
RESTIC_PASSWORD_FILE="/home/duane/resticlvm/secrets/repo_password.txt" # Path to Restic password file

# Paths to exclude (space-separated list)
EXCLUDE_PATHS="/dev /media /mnt /proc /run /sys /tmp /var/tmp /var/lib/libvirt/images"

# Ensure we run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo."
    exit 1
fi

# Remount /boot as read-only
echo "Remounting /boot as read-only..."
if ! mount | grep -q 'on /boot '; then
    echo "/boot is not mounted. Skipping /boot backup."
else
    BOOT_PARTITION=$(mount | grep 'on /boot ' | awk '{print $1}')
    mount -o remount,ro $BOOT_PARTITION
    if [ $? -ne 0 ]; then
        echo "Failed to remount /boot as read-only. Exiting."
        exit 1
    fi
fi

# Run Restic backup for /boot
echo "Running Restic backup for /boot..."
restic -r $RESTIC_REPO_BOOT --password-file=$RESTIC_PASSWORD_FILE backup /boot --verbose
if [ $? -ne 0 ]; then
    echo "Restic backup for /boot failed."
fi

# Remount /boot as read-write
if [ -n "$BOOT_PARTITION" ]; then
    echo "Remounting /boot as read-write..."
    mount -o remount,rw $BOOT_PARTITION
    if [ $? -ne 0 ]; then
        echo "Failed to remount /boot as read-write. Please check manually."
    fi
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
echo "Binding Restic repository..."
mkdir -p $SNAPSHOT_MOUNT_POINT$(dirname $RESTIC_REPO_ROOT)
mount --bind $(dirname $RESTIC_REPO_ROOT) $SNAPSHOT_MOUNT_POINT$(dirname $RESTIC_REPO_ROOT)

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
echo "Running Restic backup..."
chroot $SNAPSHOT_MOUNT_POINT /bin/bash -c "
  export RESTIC_PASSWORD_FILE=$RESTIC_PASSWORD_FILE
  restic $EXCLUDE_ARGS -r $RESTIC_REPO_ROOT backup / --verbose
"



# Exit chroot and clean up
echo "Cleaning up..."
umount $SNAPSHOT_MOUNT_POINT/dev
umount $SNAPSHOT_MOUNT_POINT/proc
umount $SNAPSHOT_MOUNT_POINT/sys
umount $SNAPSHOT_MOUNT_POINT$(dirname $RESTIC_REPO_ROOT)
umount $SNAPSHOT_MOUNT_POINT
lvremove -y /dev/$VG_NAME/$SNAP_NAME
rmdir $SNAPSHOT_MOUNT_POINT

echo "Backup completed successfully."
