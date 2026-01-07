#!/bin/bash
# Central configuration for VM disk sizes and build resources
# Source this file in build/deploy scripts to ensure consistency
#
# Usage:
#   source "$(dirname "$0")/../common/config/vm-sizes.sh"

# ============================================================================
# DISK SIZES
# ============================================================================

# Packer Build Disk Sizes
# ------------------------
# Source image disk: Temporary disk that holds the base cloud image during build.
#   - Must be >= cloud image size (Debian cloud images are ~2GB)
#   - Gets resized from cloud image
#   - In deployed VMs, becomes temporary disk cleaned up after LVM migration
export VM_SOURCE_IMAGE_DISK_SIZE="10G"

# LVM disk: Main root filesystem disk
#   - Created during Packer build as additional disk
#   - Becomes the final root filesystem after LVM migration
#   - Should match deployment LVM_DISK_SIZE
export VM_LVM_DISK_SIZE="15G"

# LVM root logical volume size
#   - Size of the lv_root logical volume in vg0
#   - Should be less than VM_LVM_DISK_SIZE to leave free space in VG
#   - Free space = VM_LVM_DISK_SIZE - VM_LVM_LV_ROOT_SIZE
#   - Set equal to VM_LVM_DISK_SIZE to use all available space
export VM_LVM_LV_ROOT_SIZE="10G"

# Backup disk: Additional LVM disk for /srv/backup
#   - Created during Packer build as additional disk
#   - Becomes separate LVM volume mounted at /srv/backup
#   - Should match deployment BACKUP_DISK_SIZE
export VM_BACKUP_DISK_SIZE="10G"

# Data LVM disk: Test disk with LVM for /srv/data_lv
#   - 5G volume group with 2G logical volume
#   - Used for testing LVM snapshots with small dataset
export VM_DATA_LV_DISK_SIZE="5G"
export VM_DATA_LV_LV_SIZE="2G"

# Data standard partition: Test disk with regular partition for /srv/data_standard_partition
#   - 5G standard ext4 partition (no LVM)
#   - Used for comparison testing vs LVM
export VM_DATA_PARTITION_DISK_SIZE="1G"

# Deployment Disk Sizes
# ---------------------
# EFI disk: Dedicated /boot/efi partition
#   - Created fresh during deployment (not from Packer image)
#   - Contains bootloader and kernels
#   - 2GB allows multiple kernel versions
export VM_EFI_DISK_SIZE="2G"

# Note: VM_LVM_DISK_SIZE and VM_BACKUP_DISK_SIZE used for both build and deployment


# ============================================================================
# BUILD RESOURCES
# ============================================================================

# Resources for VMs during Packer build (not final deployed VM)
export VM_BUILD_MEMORY="2048"  # MB
export VM_BUILD_CPUS="2"

# Default resources for deployed VMs
export VM_DEPLOY_MEMORY="4096"  # MB
export VM_DEPLOY_VCPUS="4"


# ============================================================================
# PLATFORM-SPECIFIC OVERRIDES
# ============================================================================

# AWS Configuration
# -----------------
export AWS_REGION="us-west-2"
export AWS_PROFILE="default"  # AWS CLI profile to use

# AWS Packer Build Instance
export AWS_BUILD_INSTANCE_TYPE="t3.small"  # For running Packer builds

# AWS Deployed Instance Defaults
export AWS_DEFAULT_INSTANCE_TYPE="t3.small"
export AWS_DEFAULT_REGION="us-west-2"

# AWS Disk Sizes (EBS volumes)
# Note: AWS uses same logical layout as local (EFI + LVM + Backup)
# but implements differently (3 EBS volumes instead of qcow2 files)
# Root volume must be >= source AMI size (Debian 13 AMI is 8GB)
export AWS_ROOT_VOLUME_SIZE="8"     # GB (for /boot/efi, must be >= source AMI)
export AWS_LVM_VOLUME_SIZE="10"     # GB (for LVM root physical disk)
export AWS_LVM_LV_ROOT_SIZE="8"     # GB (for lv_root logical volume, <= AWS_LVM_VOLUME_SIZE)
export AWS_BACKUP_VOLUME_SIZE="20"  # GB (for backup LVM)
export AWS_VOLUME_TYPE="gp3"        # EBS volume type (gp3 is latest/best price-performance)

# Debian official AWS AMI
export DEBIAN_AWS_ACCOUNT_ID="136693071363"  # Official Debian AWS account
export DEBIAN_AMI_NAME_FILTER="debian-13-amd64-*"


# ============================================================================
# VALIDATION
# ============================================================================

# Ensure sizes are valid (basic check)
if [ -n "$VM_SIZES_DEBUG" ]; then
  echo "VM Size Configuration Loaded:"
  echo "  Source Image Disk: $VM_SOURCE_IMAGE_DISK_SIZE"
  echo "  LVM Disk:          $VM_LVM_DISK_SIZE"
  echo "  LVM LV Root:       $VM_LVM_LV_ROOT_SIZE"
  echo "  Backup Disk:       $VM_BACKUP_DISK_SIZE"
  echo "  Data LV Disk:      $VM_DATA_LV_DISK_SIZE (LV: $VM_DATA_LV_LV_SIZE)"
  echo "  Data Part Disk:    $VM_DATA_PARTITION_DISK_SIZE"
  echo "  EFI Disk:          $VM_EFI_DISK_SIZE"
  echo "  Build Memory:      ${VM_BUILD_MEMORY}MB"
  echo "  Build CPUs:        $VM_BUILD_CPUS"
  echo "  Deploy Memory:     ${VM_DEPLOY_MEMORY}MB"
  echo "  Deploy vCPUs:      $VM_DEPLOY_VCPUS"
fi
