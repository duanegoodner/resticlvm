#!/bin/bash
# Convert PARTUUID to UUID in /etc/fstab

set -e

echo "Converting PARTUUID to UUID for disk portability..."

# Debug: show available block devices
echo "Available block devices:"
lsblk
echo ""
sudo blkid

# Find the root filesystem
ROOT_DEV=$(df / | tail -1 | awk '{print $1}')
echo "Root device: $ROOT_DEV"

# Get the UUID of the root filesystem
ROOT_UUID=$(sudo blkid -s UUID -o value "$ROOT_DEV")

if [ -z "$ROOT_UUID" ]; then
    echo "ERROR: Could not get UUID for $ROOT_DEV"
    exit 1
fi

echo "Root filesystem UUID: $ROOT_UUID"

# Replace only the root filesystem PARTUUID with UUID in fstab (not the EFI partition)
sudo sed -i "0,/^PARTUUID=[^ ]*/{s|^PARTUUID=[^ ]*|UUID=$ROOT_UUID|}" /etc/fstab

# Show the updated fstab
echo "Updated /etc/fstab:"
cat /etc/fstab

echo "Conversion complete"
