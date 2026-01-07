#!/bin/bash

# Cleanup cloud image disk after successful LVM migration
# Run this after VM has rebooted into LVM root

set -e

VM_NAME="${1:-debian13-vm}"
DISK_DIR="/var/lib/libvirt/images"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== Cleanup Cloud Image Disk ===${NC}"
echo ""

# Check if VM exists
if ! sudo virsh dominfo "$VM_NAME" &>/dev/null; then
    echo -e "${RED}Error: VM '$VM_NAME' not found${NC}"
    exit 1
fi

# Check if VM is running
if sudo virsh list --state-running | grep -q "$VM_NAME"; then
    echo "VM is running. Checking if migration completed..."
    
    # Try to check if system is running on LVM
    # (This is a simple check - you might want to make it more robust)
    if sudo virsh domblklist "$VM_NAME" | grep -q "vda"; then
        echo -e "${YELLOW}vda disk is still attached${NC}"
        echo ""
        echo "To cleanup:"
        echo "  1. Verify VM is running on LVM: sudo virsh console $VM_NAME"
        echo "     Run: df -h | grep vg0-lv_root"
        echo "  2. If confirmed, shutdown VM: sudo virsh shutdown $VM_NAME"
        echo "  3. Run this script again"
        exit 0
    fi
else
    echo "VM is shut down. Proceeding with cleanup..."
fi

# Detach vda disk
echo -e "${YELLOW}Detaching vda disk...${NC}"
if sudo virsh detach-disk "$VM_NAME" vda --config --persistent 2>/dev/null; then
    echo -e "${GREEN}✓ vda disk detached${NC}"
else
    echo -e "${YELLOW}Note: vda disk may already be detached${NC}"
fi

# Delete the disk file
BOOT_DISK="${DISK_DIR}/${VM_NAME}-boot.qcow2"
if [ -f "$BOOT_DISK" ]; then
    echo -e "${YELLOW}Deleting boot disk file...${NC}"
    sudo rm "$BOOT_DISK"
    echo -e "${GREEN}✓ Boot disk deleted${NC}"
    
    # Calculate space saved
    echo ""
    echo -e "${GREEN}Cleanup complete! Saved ~10GB of disk space.${NC}"
else
    echo -e "${YELLOW}Boot disk file not found (may already be deleted)${NC}"
fi

# Start VM if it was shut down
if ! sudo virsh list --state-running | grep -q "$VM_NAME"; then
    echo ""
    read -p "Start VM now? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo virsh start "$VM_NAME"
        echo -e "${GREEN}VM started${NC}"
        echo ""
        echo "Verify final layout:"
        echo "  sudo virsh console $VM_NAME"
        echo "  Then run: lsblk"
        echo ""
        echo "Expected output:"
        echo "  vdb1: /boot/efi"
        echo "  vdc (LVM): /"
    fi
fi

echo ""
echo -e "${GREEN}Done!${NC}"
