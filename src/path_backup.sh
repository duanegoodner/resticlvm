#!/bin/bash

# Default values (optional)
EXCLUDE_PATHS=""
REMOUNT_AS_RO="false"

# Parse named arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
    --restic-repo)
        RESTIC_REPO="$2"
        shift 2
        ;;
    --password-file)
        RESTIC_PASSWORD_FILE="$2"
        shift 2
        ;;
    --backup-source)
        BACKUP_SOURCE="$2"
        shift 2
        ;;
    --exclude-paths)
        EXCLUDE_PATHS="$2"
        shift 2
        ;;
    --remount-as-ro)
        REMOUNT_AS_RO="$2"
        shift 2
        ;;
    *)
        echo "Unknown option: $1"
        exit 1
        ;;
    esac
done

# Validate required args
if [[ -z "$RESTIC_REPO" || -z "$RESTIC_PASSWORD_FILE" || -z "$BACKUP_SOURCE" ]]; then
    echo "Usage: $0 --restic-repo PATH --password-file PATH --backup-source PATH [--exclude-paths PATHS] [--remount-as-ro true|false]"
    exit 1
fi

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
