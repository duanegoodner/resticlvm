#!/bin/bash

# Set variables
RESTIC_REPO="/backup/restic/restic-boot"
RESTIC_PASSWORD_FILE="/home/duane/resticlvm/secrets/repo_password.txt"
BACKUP_SOURCE="/boot"
EXCLUDE_PATHS=""

REMOUNT_AS_RO=true # Set to false to skip remounting

# Ensure we run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo."
    exit 1
fi

# Optionally remount the backup source as read-only
if [ "$REMOUNT_AS_RO" = true ]; then
    echo "Remounting ${BACKUP_SOURCE} as read-only..."

    if ! mountpoint -q "$BACKUP_SOURCE"; then
        echo "Warning: ${BACKUP_SOURCE} is not a mount point. Skipping remount."
    else
        PARTITION_DEV=$(findmnt -n -o SOURCE --target "$BACKUP_SOURCE")
        mount -o remount,ro "$PARTITION_DEV"
        if [ $? -ne 0 ]; then
            echo "Failed to remount ${BACKUP_SOURCE} as read-only. Exiting."
            exit 1
        fi
    fi
fi

# Convert exclude paths to a Restic-compatible array
EXCLUDE_ARGS=()
for path in $EXCLUDE_PATHS; do
    EXCLUDE_ARGS+=("--exclude=$path")
done

# Run Restic backup
echo "Running Restic backup for ${BACKUP_SOURCE}..."
restic -r "$RESTIC_REPO" --password-file="$RESTIC_PASSWORD_FILE" backup "$BACKUP_SOURCE" "${EXCLUDE_ARGS[@]}" --verbose

if [ $? -ne 0 ]; then
    echo "Restic backup for ${BACKUP_SOURCE} failed."
fi

# Remount back to read-write if needed
if [ "$REMOUNT_AS_RO" = true ] && mountpoint -q "$BACKUP_SOURCE"; then
    echo "Remounting ${BACKUP_SOURCE} as read-write..."
    PARTITION_DEV=$(findmnt -n -o SOURCE --target "$BACKUP_SOURCE")
    mount -o remount,rw "$PARTITION_DEV"
    if [ $? -ne 0 ]; then
        echo "Failed to remount ${BACKUP_SOURCE} as read-write. Please check manually."
    fi
fi
