#!/bin/bash
# Setup LVM on the second and third EBS volumes
# /dev/xvdf - for root filesystem (vg0-lv_root)
# /dev/xvdg - for backup (vg1-lv_backup)
# This script prepares the LVM infrastructure but doesn't migrate data yet

set -e

# LV size can be set via environment variable (default: use all space)
LVM_LV_ROOT_SIZE="${LVM_LV_ROOT_SIZE:-100%FREE}"

echo "=== Setting up LVM on /dev/xvdf and /dev/xvdg ==="
echo "LV Root Size: $LVM_LV_ROOT_SIZE"

# Identify the LVM disk for root (should be /dev/xvdf or /dev/nvme1n1 depending on instance type)
if [ -b /dev/xvdf ]; then
    LVM_DISK="/dev/xvdf"
    BACKUP_DISK="/dev/xvdg"
elif [ -b /dev/nvme1n1 ]; then
    LVM_DISK="/dev/nvme1n1"
    BACKUP_DISK="/dev/nvme2n1"
else
    echo "Error: Could not find LVM disk (tried /dev/xvdf and /dev/nvme1n1)"
    lsblk
    exit 1
fi

echo "Using LVM disk: $LVM_DISK"
echo "Using Backup disk: $BACKUP_DISK"

# Create physical volume for root
echo "Creating physical volume for root..."
sudo pvcreate "$LVM_DISK"

# Create volume group for root
echo "Creating volume group vg0..."
sudo vgcreate vg0 "$LVM_DISK"

# Create logical volume
echo "Creating logical volume lv_root (size: $LVM_LV_ROOT_SIZE)..."
sudo lvcreate -L "$LVM_LV_ROOT_SIZE" -n lv_root vg0

# Format the logical volume
echo "Formatting /dev/vg0/lv_root with ext4..."
sudo mkfs.ext4 /dev/vg0/lv_root

# Show VG status
sudo vgs vg0

echo "Root LVM setup complete!"

# Setup backup LVM if backup disk exists
if [ -b "$BACKUP_DISK" ]; then
    echo "Setting up backup LVM on $BACKUP_DISK..."
    
    # Create physical volume for backup
    echo "Creating physical volume for backup..."
    sudo pvcreate "$BACKUP_DISK"
    
    # Create volume group for backup
    echo "Creating volume group vg1..."
    sudo vgcreate vg1 "$BACKUP_DISK"
    
    # Create logical volume using all available space
    echo "Creating logical volume lv_backup..."
    sudo lvcreate -l 100%FREE -n lv_backup vg1
    
    # Format the logical volume
    echo "Formatting /dev/vg1/lv_backup with ext4..."
    sudo mkfs.ext4 /dev/vg1/lv_backup
    
    echo "Backup LVM setup complete!"
else
    echo "Warning: Backup disk $BACKUP_DISK not found, skipping backup LVM setup"
fi

echo "All LVM setup complete!"
sudo pvdisplay
sudo vgdisplay
sudo lvdisplay
