#!/bin/bash

# Set variables
RESTIC_REPO="/backup/restic/restic-boot/"
RESTIC_PASSWORD_FILE="/home/duane/resticlvm/secrets/repo_password.txt" # Path to Restic password file
BACKUP_SOURCE="/boot"

# Paths to exclude (space-separated list)
EXCLUDE_PATHS=""

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
restic -r $RESTIC_REPO --password-file=$RESTIC_PASSWORD_FILE backup /boot --verbose
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