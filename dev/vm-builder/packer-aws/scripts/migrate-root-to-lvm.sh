#!/bin/bash
# Migrate root filesystem to LVM
# This script copies the current root to the LVM volume and reconfigures the system

set -e

echo "=== Migrating root filesystem to LVM ==="

# Mount the new LVM root
echo "Mounting /dev/vg0/lv_root to /mnt..."
sudo mkdir -p /mnt
sudo mount /dev/vg0/lv_root /mnt

# Copy root filesystem to LVM (excluding special filesystems)
echo "Copying root filesystem to LVM (this may take a few minutes)..."
sudo rsync -aAXv --exclude={"/dev/*","/proc/*","/sys/*","/tmp/*","/run/*","/mnt/*","/media/*","/lost+found"} / /mnt/

# Get the UUID of the new LVM root
NEW_ROOT_UUID=$(sudo blkid -s UUID -o value /dev/vg0/lv_root)
echo "New LVM root UUID: $NEW_ROOT_UUID"

# Update fstab on the new root
echo "Updating /etc/fstab..."
sudo sed -i "s|^[^#].*\s/\s|UUID=$NEW_ROOT_UUID / ext4 defaults 0 1|" /mnt/etc/fstab

# Create /boot/efi mount point in new root if it doesn't exist
sudo mkdir -p /mnt/boot/efi

# Add /boot/efi entry to fstab (will use /dev/xvda1 which will be the EFI partition)
# Note: We'll set this up properly after the migration is complete
echo "# /boot/efi will be on /dev/xvda1" | sudo tee -a /mnt/etc/fstab

# Setup backup volume in fstab if it exists
if sudo lvdisplay /dev/vg1/lv_backup &>/dev/null; then
    echo "Adding backup volume to fstab..."
    BACKUP_UUID=$(sudo blkid -s UUID -o value /dev/vg1/lv_backup)
    echo "UUID=$BACKUP_UUID /srv/backup ext4 defaults 0 2" | sudo tee -a /mnt/etc/fstab
    
    # Create backup mount point in new root
    sudo mkdir -p /mnt/srv/backup
fi

# Update GRUB configuration for new root
echo "Updating GRUB configuration..."
# Mount necessary filesystems for chroot
sudo mount --bind /dev /mnt/dev
sudo mount --bind /proc /mnt/proc
sudo mount --bind /sys /mnt/sys

# Update grub config to point to LVM root
sudo chroot /mnt /bin/bash -c "
    # Update /etc/default/grub to use LVM root
    sed -i 's|^GRUB_CMDLINE_LINUX=.*|GRUB_CMDLINE_LINUX=\"root=/dev/mapper/vg0-lv_root\"|' /etc/default/grub
    
    # Rebuild initramfs to include LVM modules
    update-initramfs -u -k all
    
    # Update GRUB
    update-grub
"

# Unmount chroot filesystems
sudo umount /mnt/sys
sudo umount /mnt/proc
sudo umount /mnt/dev
sudo umount /mnt

echo "Root filesystem migration complete!"
echo "The system will boot from LVM after AMI is created and instance is launched."
