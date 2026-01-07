#!/bin/bash

# Post-installation script to migrate cloud image to LVM with separate EFI disk and backup volume
# Final layout:
#   EFI_DISK: EFI partition mounted at /boot/efi
#   LVM_DISK: LVM (vg0-lv_root) mounted at / (contains /boot directory)
#   BACKUP_DISK: LVM (vg1-lv_backup) mounted at /srv/backup
#   DATA_LV_DISK: LVM (vg2-lv_data) mounted at /srv/data_lv
#   DATA_PARTITION_DISK: Standard partition mounted at /srv/data_standard_partition
#   BOOT_DISK: Original cloud image (to be deleted after successful migration)
#
# Environment variables (optional):
#   EFI_DISK: Disk for EFI partition (default: /dev/vdb)
#   LVM_DISK: Disk for LVM root (default: /dev/vdc)
#   LVM_LV_ROOT_SIZE: Size for lv_root logical volume (default: 100%FREE)
#   BACKUP_DISK: Disk for backup LVM (default: /dev/vdd)
#   DATA_LV_DISK: Disk for data LVM (default: /dev/vde)
#   DATA_LV_SIZE: Size for lv_data logical volume (default: 2G)
#   DATA_PARTITION_DISK: Disk for standard partition (default: /dev/vdf)
#   BOOT_DISK: Original boot disk (default: /dev/vda)
#   CURRENT_EFI: Current EFI partition (default: /dev/vda15)

set -e

echo "=== LVM Root Migration (First Boot) ==="

# Check if already running on LVM root
ROOT_DEV=$(findmnt -n -o SOURCE /)
if [[ "$ROOT_DEV" == "/dev/mapper/vg0-lv_root" ]] || [[ "$ROOT_DEV" == "/dev/vg0/lv_root" ]]; then
    echo "Already running on LVM root filesystem. Migration complete."
    exit 0
fi

# Note about cloud-init - we don't wait for it since it can run in parallel
echo "Note: cloud-init may still be running in parallel - this is normal"
echo ""

# Disk configuration (with environment variable overrides)
EFI_DISK="${EFI_DISK:-/dev/vdb}"        # Will hold EFI partition
LVM_DISK="${LVM_DISK:-/dev/vdc}"        # Will hold LVM root
LVM_LV_ROOT_SIZE="${LVM_LV_ROOT_SIZE:-100%FREE}"  # Size for lv_root (can be specific size like 8G)
BACKUP_DISK="${BACKUP_DISK:-/dev/vdd}"  # Will hold backup LVM
DATA_LV_DISK="${DATA_LV_DISK:-/dev/vde}"  # Will hold data LVM
DATA_LV_SIZE="${DATA_LV_SIZE}"          # Size for lv_data logical volume (set by service)
DATA_PARTITION_DISK="${DATA_PARTITION_DISK:-/dev/vdf}"  # Will hold standard partition
BOOT_DISK="${BOOT_DISK:-/dev/vda}"      # Original boot disk
CURRENT_EFI="${CURRENT_EFI:-/dev/vda15}" # EFI partition in cloud image
EFI_PART="${EFI_DISK}1"
DATA_PARTITION="${DATA_PARTITION_DISK}1"

echo "Configuration:"
echo "  EFI Disk:         $EFI_DISK"
echo "  LVM Disk:         $LVM_DISK"
echo "  LV Root Size:     $LVM_LV_ROOT_SIZE"
echo "  Backup Disk:      $BACKUP_DISK"
echo "  Data LV Disk:     $DATA_LV_DISK"
echo "  Data LV Size:     $DATA_LV_SIZE"
echo "  Data Part Disk:   $DATA_PARTITION_DISK"
echo "  Boot Disk:        $BOOT_DISK"
echo "  Current EFI:      $CURRENT_EFI"

# Verify disks exist
if [ ! -b "$EFI_DISK" ]; then
    echo "Error: $EFI_DISK not found. Is the EFI disk attached?"
    exit 1
fi

if [ ! -b "$LVM_DISK" ]; then
    echo "Error: $LVM_DISK not found. Is the LVM disk attached?"
    exit 1
fi

if [ ! -b "$BACKUP_DISK" ]; then
    echo "Warning: $BACKUP_DISK not found. Backup volume will not be created."
    BACKUP_DISK=""
else
    echo "Found Backup disk: $BACKUP_DISK"
fi

echo "Found EFI disk: $EFI_DISK"
echo "Found LVM disk: $LVM_DISK"

# Check if LVM setup exists, if not create it
echo "Checking LVM configuration..."
if ! lvdisplay /dev/vg0/lv_root &>/dev/null; then
    echo "Creating LVM structure on $LVM_DISK..."
    
    # Create LVM structure
    pvcreate "$LVM_DISK"
    vgcreate vg0 "$LVM_DISK"
    lvcreate -L "$LVM_LV_ROOT_SIZE" -n lv_root vg0
    mkfs.ext4 /dev/vg0/lv_root
    
    # Show VG status to display free space
    vgs vg0
    echo "LVM setup complete!"
else
    echo "LVM already exists."
fi

# Create backup LVM if backup disk exists
if [ -n "$BACKUP_DISK" ]; then
    echo "Checking backup LVM configuration..."
    if ! lvdisplay /dev/vg1/lv_backup &>/dev/null; then
        echo "Creating backup LVM structure on $BACKUP_DISK..."
        
        # Create backup LVM structure
        pvcreate "$BACKUP_DISK"
        vgcreate vg1 "$BACKUP_DISK"
        lvcreate -l 100%FREE -n lv_backup vg1
        mkfs.ext4 /dev/vg1/lv_backup
        echo "Backup LVM setup complete!"
    else
        echo "Backup LVM already exists."
    fi
fi

# Create data LVM if data LV disk exists
if [ -n "$DATA_LV_DISK" ]; then
    echo "Checking data LVM configuration..."
    if ! lvdisplay /dev/vg2/lv_data &>/dev/null; then
        echo "Creating data LVM structure on $DATA_LV_DISK..."
        
        # Create data LVM structure (vg2 with lv_data)
        pvcreate "$DATA_LV_DISK"
        vgcreate vg2 "$DATA_LV_DISK"
        lvcreate -L "$DATA_LV_SIZE" -n lv_data vg2
        mkfs.ext4 /dev/vg2/lv_data
        
        # Show VG status to display free space
        vgs vg2
        echo "Data LVM setup complete!"
    else
        echo "Data LVM already exists."
    fi
fi

# Create standard partition if data partition disk exists
if [ -n "$DATA_PARTITION_DISK" ]; then
    echo "Checking data partition configuration..."
    if ! blkid "$DATA_PARTITION" &>/dev/null; then
        echo "Creating standard partition on $DATA_PARTITION_DISK..."
        
        # Create partition table and partition
        parted -s "$DATA_PARTITION_DISK" mklabel gpt
        parted -s "$DATA_PARTITION_DISK" mkpart primary ext4 0% 100%
        
        # Force kernel to re-read partition table
        partprobe "$DATA_PARTITION_DISK"
        sleep 1  # Give kernel a moment to register the new partition
        
        # Format partition
        mkfs.ext4 "$DATA_PARTITION"
        echo "Standard partition setup complete!"
    else
        echo "Data partition already exists."
    fi
fi

# Create EFI partition on vdb
echo "Creating EFI partition on $EFI_DISK..."
parted -s "$EFI_DISK" mklabel gpt
parted -s "$EFI_DISK" mkpart ESP fat32 1MiB 100%
parted -s "$EFI_DISK" set 1 esp on
partprobe "$EFI_DISK"
sleep 2

# Format EFI partition
echo "Formatting EFI partition..."
mkfs.vfat -F 32 "$EFI_PART"

# Mount the new root and copy everything
echo "Mounting new root filesystem..."
mkdir -p /mnt/newroot
mount /dev/vg0/lv_root /mnt/newroot

# Mount new EFI partition
echo "Mounting new EFI partition..."
mkdir -p /mnt/newefi
mount "$EFI_PART" /mnt/newefi

echo "Copying root filesystem to LVM volume (this may take a few minutes)..."
rsync -aAXv \
  --exclude=/dev/* \
  --exclude=/proc/* \
  --exclude=/sys/* \
  --exclude=/tmp/* \
  --exclude=/run/* \
  --exclude=/mnt/* \
  --exclude=/media/* \
  --exclude=/lost+found \
  --exclude=/boot/efi/* \
  / /mnt/newroot/

echo "Copying EFI files to new EFI partition..."
if [ -d /boot/efi ]; then
    rsync -aAXv /boot/efi/ /mnt/newefi/
fi

# Update fstab in new root
echo "Updating /etc/fstab..."
ROOT_UUID=$(blkid -s UUID -o value /dev/vg0/lv_root)
EFI_UUID=$(blkid -s UUID -o value "$EFI_PART")
cat > /mnt/newroot/etc/fstab << EOF
# /etc/fstab: static file system information.
UUID=$ROOT_UUID  /         ext4    defaults        0       1
UUID=$EFI_UUID   /boot/efi vfat    defaults,umask=077 0 2
EOF

# Add backup volume to fstab if it exists
if [ -n "$BACKUP_DISK" ]; then
    BACKUP_UUID=$(blkid -s UUID -o value /dev/vg1/lv_backup)
    echo "UUID=$BACKUP_UUID  /srv/backup ext4    defaults        0       2" >> /mnt/newroot/etc/fstab
    
    # Create backup mount point in new root
    mkdir -p /mnt/newroot/srv/backup
fi

# Add data LV to fstab if it exists
if [ -n "$DATA_LV_DISK" ]; then
    DATA_LV_UUID=$(blkid -s UUID -o value /dev/vg2/lv_data)
    echo "UUID=$DATA_LV_UUID  /srv/data_lv ext4    defaults        0       2" >> /mnt/newroot/etc/fstab
    
    # Create data_lv mount point in new root
    mkdir -p /mnt/newroot/srv/data_lv
fi

# Add data partition to fstab if it exists
if [ -n "$DATA_PARTITION_DISK" ]; then
    DATA_PART_UUID=$(blkid -s UUID -o value "$DATA_PARTITION")
    echo "UUID=$DATA_PART_UUID  /srv/data_standard_partition ext4    defaults        0       2" >> /mnt/newroot/etc/fstab
    
    # Create data_standard_partition mount point in new root
    mkdir -p /mnt/newroot/srv/data_standard_partition
fi

# Chroot and update GRUB
echo "Updating GRUB configuration..."
mount --bind /dev /mnt/newroot/dev
mount --bind /proc /mnt/newroot/proc
mount --bind /sys /mnt/newroot/sys
mount "$EFI_PART" /mnt/newroot/boot/efi

echo "Updating initramfs..."
chroot /mnt/newroot update-initramfs -u -k all

echo "Updating GRUB..."
chroot /mnt/newroot update-grub

echo "Installing GRUB to EFI partition..."
chroot /mnt/newroot grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=debian

# Cleanup
echo "Unmounting filesystems..."
umount /mnt/newroot/boot/efi
umount /mnt/newroot/dev
umount /mnt/newroot/proc
umount /mnt/newroot/sys
umount /mnt/newroot
umount /mnt/newefi

echo ""
echo "=== LVM Migration Complete ==="
echo ""
echo "Final disk layout:"
echo "  vdb1: EFI partition (/boot/efi)"
echo "  vdc:  LVM root (/) with /boot directory"
if [ -n "$BACKUP_DISK" ]; then
    echo "  vdd:  LVM backup (/srv/backup)"
fi
if [ -n "$DATA_LV_DISK" ]; then
    echo "  vde:  LVM data (/srv/data_lv) - vg2/lv_data $DATA_LV_SIZE in $(echo $VM_DATA_LV_DISK_SIZE | sed 's/G//') GB VG"
fi
if [ -n "$DATA_PARTITION_DISK" ]; then
    echo "  vdf1: Standard partition (/srv/data_standard_partition)"
fi
echo "  vda:  Original cloud image (can be deleted after successful boot)"
echo ""
echo "Rebooting system to activate new layout..."
echo ""

sleep 5
reboot
