#!/bin/bash

# Deploy Packer-built image to local KVM

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Load central configuration
source "$SCRIPT_DIR/../common/config/vm-sizes.sh"

# Default values
VM_NAME="debian13-vm"
MEMORY=${VM_DEPLOY_MEMORY}
VCPUS=${VM_DEPLOY_VCPUS}

# Disk sizes from central config (can be overridden via command-line)
EFI_DISK_SIZE=${VM_EFI_DISK_SIZE%G}     # Remove G suffix for script processing
LVM_DISK_SIZE=${VM_LVM_DISK_SIZE%G}     # Remove G suffix for script processing
BACKUP_DISK_SIZE=${VM_BACKUP_DISK_SIZE%G} # Remove G suffix for script processing

NETWORK="default"
DISK_DIR="/var/lib/libvirt/images"
IMAGE_PATH=""
SSH_KEY=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --image)
      IMAGE_PATH="$2"
      shift 2
      ;;
    --name)
      VM_NAME="$2"
      shift 2
      ;;
    --memory)
      MEMORY="$2"
      shift 2
      ;;
    --vcpus)
      VCPUS="$2"
      shift 2
      ;;
    --lvm-disk-size)
      LVM_DISK_SIZE="${2%G}"  # Remove G suffix if present
      shift 2
      ;;
    --backup-disk-size)
      BACKUP_DISK_SIZE="${2%G}"  # Remove G suffix if present
      shift 2
      ;;
    --efi-disk-size)
      EFI_DISK_SIZE="${2%G}"  # Remove G suffix if present
      shift 2
      ;;
    --ssh-key)
      SSH_KEY="$2"
      shift 2
      ;;
    --network)
      NETWORK="$2"
      shift 2
      ;;
    *)
      # Assume first positional arg is image path
      if [ -z "$IMAGE_PATH" ]; then
        IMAGE_PATH="$1"
      fi
      shift
      ;;
  esac
done

echo -e "${BLUE}=== Deploy to Local KVM ===${NC}"
echo ""

# Validate image path
if [ -z "$IMAGE_PATH" ]; then
  echo -e "${RED}Error: No image specified${NC}"
  echo "Usage: $0 <image-path> [options]"
  echo ""
  echo "Options:"
  echo "  --name <vm-name>         VM name (default: debian13-vm)"
  echo "  --memory <mb>            RAM in MB (default: 4096)"
  echo "  --vcpus <count>          vCPUs (default: 4)"
  echo "  --efi-disk-size <size>   EFI disk size (default: 2G)"
  echo "  --lvm-disk-size <size>   LVM disk size (default: 10G)"
  echo "  --backup-disk-size <size> Backup disk size (default: 20G)"
  echo "  --ssh-key <path>         SSH public key file"
  echo "  --network <name>         Network (default: default)"
  exit 1
fi

if [ ! -f "$IMAGE_PATH" ]; then
  echo -e "${RED}Error: Image not found: $IMAGE_PATH${NC}"
  exit 1
fi

# Check for required tools
for cmd in virt-install virsh qemu-img cloud-localds; do
  if ! command -v $cmd &> /dev/null; then
    echo -e "${RED}Error: $cmd not found${NC}"
    echo "Install: sudo apt install qemu-kvm libvirt-daemon-system virtinst cloud-image-utils"
    exit 1
  fi
done

echo -e "${GREEN}Configuration:${NC}"
echo "  VM Name:      $VM_NAME"
echo "  Memory:       ${MEMORY}MB"
echo "  vCPUs:        $VCPUS"
echo "  EFI Disk:     ${EFI_DISK_SIZE}GB"
echo "  LVM Disk:     ${LVM_DISK_SIZE}GB (from central config: $VM_LVM_DISK_SIZE)"
echo "  Backup Disk:  ${BACKUP_DISK_SIZE}GB (from central config: $VM_BACKUP_DISK_SIZE)"
echo "  Network:      $NETWORK"
echo "  Source Image: $IMAGE_PATH"
echo ""

# Check if VM exists
if virsh list --all | grep -q " $VM_NAME "; then
  echo -e "${YELLOW}Warning: VM '$VM_NAME' already exists${NC}"
  read -p "Delete and recreate? (yes/no): " -r
  if [[ $REPLY == "yes" ]]; then
    echo "Destroying existing VM..."
    virsh destroy "$VM_NAME" 2>/dev/null || true
    virsh undefine "$VM_NAME" --remove-all-storage 2>/dev/null || true
  else
    echo "Aborted"
    exit 1
  fi
fi

# Prepare cloud-init
echo -e "${YELLOW}Preparing cloud-init configuration...${NC}"

CLOUD_INIT_DIR=$(mktemp -d)
trap "rm -rf $CLOUD_INIT_DIR" EXIT

# Read SSH key if provided
SSH_KEY_CONTENT=""
if [ -n "$SSH_KEY" ]; then
  if [ -f "$SSH_KEY" ]; then
    SSH_KEY_CONTENT=$(cat "$SSH_KEY")
  else
    echo -e "${YELLOW}Warning: SSH key file not found: $SSH_KEY${NC}"
  fi
fi

# Create user-data
cat > "$CLOUD_INIT_DIR/user-data" << EOF
#cloud-config
hostname: ${VM_NAME}
fqdn: ${VM_NAME}.localdomain

users:
  - name: debian
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    lock_passwd: false
EOF

if [ -n "$SSH_KEY_CONTENT" ]; then
  cat >> "$CLOUD_INIT_DIR/user-data" << EOF
    ssh_authorized_keys:
      - $SSH_KEY_CONTENT
EOF
else
  # No SSH key provided, set password
  cat >> "$CLOUD_INIT_DIR/user-data" << 'EOF'
    passwd: $6$rounds=4096$saltsaltsal$P3h4w4W1T1s2Q4F5H6J7k8L9M0N1P2Q3R4S5T6U7V8W9X0Y1Z2A3B4C5D6E7F8G9H0
EOF
fi

cat >> "$CLOUD_INIT_DIR/user-data" << 'EOF'

# Enable password authentication for initial access
ssh_pwauth: true

# Set password for debian user (password: debian)
chpasswd:
  users:
    - name: debian
      password: debian
      type: text
  expire: false

# Timezone
timezone: UTC

# Regenerate SSH host keys (removed during Packer cleanup)
ssh_deletekeys: true
ssh_genkeytypes: ['rsa', 'ecdsa', 'ed25519']

# No package updates (already done in image build)
package_update: false
package_upgrade: false

# Final message
final_message: "System boot completed in $UPTIME seconds. LVM migration will run if needed."
EOF

# Create meta-data
cat > "$CLOUD_INIT_DIR/meta-data" << EOF
instance-id: ${VM_NAME}-$(date +%s)
local-hostname: ${VM_NAME}
EOF

# Create network-config for automatic DHCP
cat > "$CLOUD_INIT_DIR/network-config" << EOF
version: 2
ethernets:
  ens3:
    dhcp4: true
    dhcp6: false
EOF

# Create cloud-init ISO
CLOUD_INIT_ISO="${DISK_DIR}/${VM_NAME}-cloudinit.iso"
sudo cloud-localds -N "$CLOUD_INIT_DIR/network-config" "$CLOUD_INIT_ISO" "$CLOUD_INIT_DIR/user-data" "$CLOUD_INIT_DIR/meta-data"

echo -e "${GREEN}✓ Cloud-init configuration ready${NC}"

# Copy boot disk (cloud image - temporary, will be deleted after migration)
echo -e "${YELLOW}Copying boot disk (cloud image, temporary)...${NC}"
BOOT_DISK="${DISK_DIR}/${VM_NAME}-boot.qcow2"
sudo cp "$IMAGE_PATH" "$BOOT_DISK"
sudo chown libvirt-qemu:kvm "$BOOT_DISK"
echo -e "${GREEN}✓ Boot disk ready (vda - temporary)${NC}"

# Create EFI disk (will hold /boot/efi)
echo -e "${YELLOW}Creating EFI disk (${EFI_DISK_SIZE}GB)...${NC}"
EFI_DISK="${DISK_DIR}/${VM_NAME}-efi.qcow2"
sudo qemu-img create -f qcow2 "$EFI_DISK" "${EFI_DISK_SIZE}G"
sudo chown libvirt-qemu:kvm "$EFI_DISK"
echo -e "${GREEN}✓ EFI disk ready (vdb - permanent)${NC}"

# Create LVM disk (will hold root filesystem)
echo -e "${YELLOW}Creating LVM disk (${LVM_DISK_SIZE}GB)...${NC}"
LVM_DISK="${DISK_DIR}/${VM_NAME}-lvm.qcow2"
sudo qemu-img create -f qcow2 "$LVM_DISK" "${LVM_DISK_SIZE}G"
sudo chown libvirt-qemu:kvm "$LVM_DISK"
echo -e "${GREEN}✓ LVM disk ready (vdc - permanent)${NC}"

# Create backup disk (will hold /srv/backup)
echo -e "${YELLOW}Creating backup disk (${BACKUP_DISK_SIZE}GB)...${NC}"
BACKUP_DISK="${DISK_DIR}/${VM_NAME}-backup.qcow2"
sudo qemu-img create -f qcow2 "$BACKUP_DISK" "${BACKUP_DISK_SIZE}G"
sudo chown libvirt-qemu:kvm "$BACKUP_DISK"
echo -e "${GREEN}✓ Backup disk ready (vdd - permanent)${NC}"

# Create VM
echo -e "${YELLOW}Creating VM...${NC}"
sudo virt-install \
  --name "$VM_NAME" \
  --memory "$MEMORY" \
  --vcpus "$VCPUS" \
  --disk path="$BOOT_DISK",format=qcow2,bus=virtio,boot_order=3 \
  --disk path="$EFI_DISK",format=qcow2,bus=virtio,boot_order=1 \
  --disk path="$LVM_DISK",format=qcow2,bus=virtio,boot_order=2 \
  --disk path="$BACKUP_DISK",format=qcow2,bus=virtio,boot_order=4 \
  --disk path="$CLOUD_INIT_ISO",device=cdrom,bus=scsi \
  --controller type=scsi,model=virtio-scsi \
  --network network="$NETWORK",model=virtio \
  --os-variant debian11 \
  --virt-type kvm \
  --machine pc \
  --graphics spice,listen=127.0.0.1 \
  --video qxl \
  --console pty,target_type=serial \
  --boot uefi \
  --import \
  --noautoconsole

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "VM '$VM_NAME' is starting..."
echo ""
echo "What happens next:"
echo "  1. VM boots from cloud image (vda - temporary)"
echo "  2. Cloud-init configures hostname, SSH keys, users"
echo "  3. LVM migration service runs automatically:"
echo "     - Creates EFI partition on vdb"
echo "     - Creates LVM on vdc for root filesystem"
echo "     - Creates LVM on vdd for backup volume"
echo "     - Migrates root filesystem to vdc LVM"
echo "     - Copies EFI files to vdb"
echo "  4. VM reboots into new layout (vdb + vdc + vdd)"
echo "  5. vda can be manually deleted after successful boot"
echo ""
echo "Final disk layout:"
echo "  vdb: EFI partition (/boot/efi)"
echo "  vdc: LVM root (/) with /boot directory inside"
echo "  vdd: LVM backup (/srv/backup)"
echo ""
echo "Commands:"
echo "  Check status:  virsh list --all"
echo "  Console:       virsh console $VM_NAME"
echo "  GUI Console:   virt-viewer $VM_NAME"
echo "  Shutdown:      virsh shutdown $VM_NAME"
echo "  Delete:        virsh destroy $VM_NAME && virsh undefine $VM_NAME --remove-all-storage"
echo ""
echo "After first boot completes, you can SSH as 'debian' user"
echo "  Password: debian (or use your SSH key if provided)"
echo ""
