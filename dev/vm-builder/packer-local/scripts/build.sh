#!/bin/bash

# Build Debian VM image for local KVM deployment

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load central configuration
source "$PROJECT_DIR/../common/config/vm-sizes.sh"
source "$PROJECT_DIR/../common/config/optional-tools.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Packer Local Build ===${NC}"
echo ""
echo "Configuration:"
echo "  Source Image Disk: $VM_SOURCE_IMAGE_DISK_SIZE"
echo "  LVM Disk:          $VM_LVM_DISK_SIZE"
echo "  Backup Disk:       $VM_BACKUP_DISK_SIZE"
echo "  Build Memory:      ${VM_BUILD_MEMORY}MB"
echo "  Build CPUs:        $VM_BUILD_CPUS"
echo ""
echo "Optional Tools:"
echo "  Miniconda:         $INSTALL_MINICONDA"
echo "  Restic:            $INSTALL_RESTIC"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v packer &> /dev/null; then
    echo -e "${RED}Error: packer not found${NC}"
    echo "Install: sudo apt install packer"
    exit 1
fi

if ! command -v ansible &> /dev/null; then
    echo -e "${RED}Error: ansible not found${NC}"
    echo "Install: sudo apt install ansible"
    exit 1
fi

if ! command -v qemu-system-x86_64 &> /dev/null; then
    echo -e "${RED}Error: QEMU not found${NC}"
    echo "Install: sudo apt install qemu-kvm"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites found${NC}"
echo ""

# Change to project directory
cd "$PROJECT_DIR"

# Initialize Packer plugins if needed
if [ ! -d ".packer.d" ]; then
    echo -e "${YELLOW}Initializing Packer plugins...${NC}"
    packer init .
    echo ""
fi

# Validate Packer configuration (syntax only)
echo -e "${YELLOW}Validating Packer configuration...${NC}"
packer validate -syntax-only .
echo -e "${GREEN}✓ Configuration valid${NC}"
echo ""

# Build
echo -e "${YELLOW}Starting build...${NC}"
echo -e "${BLUE}This will:${NC}"
echo "  1. Download Debian genericcloud base image (if not cached)"
echo "  2. Start QEMU VM with cloud-init"
echo "  3. Run Ansible provisioning (base, lvm, development)"
echo "  4. Create final image in output/"
echo ""
echo -e "${YELLOW}Note: Using -force to overwrite existing output${NC}"
echo ""

# Pass configuration to Packer via command-line variables
packer build -force \
  -var "source_image_disk_size=$VM_SOURCE_IMAGE_DISK_SIZE" \
  -var "lvm_disk_size=$VM_LVM_DISK_SIZE" \
  -var "backup_disk_size=$VM_BACKUP_DISK_SIZE" \
  -var "build_memory=$VM_BUILD_MEMORY" \
  -var "build_cpus=$VM_BUILD_CPUS" \
  .

echo ""
echo -e "${GREEN}=== Build Complete ===${NC}"
echo ""
echo "Output:"
ls -lh output/debian13-local/
echo ""
echo "Images created:"
echo "  Boot disk:   output/debian13-local/debian13-local"
echo "  LVM disk:    output/debian13-local/debian13-local-1"
echo "  Backup disk: output/debian13-local/debian13-local-2"
echo ""
echo "Next steps:"
echo "  Deploy: cd ../deploy-local && ./deploy.sh ../packer-local/output/debian13-local/debian13-local"
echo ""
