#!/bin/bash
# Shared version numbers and URLs for VM builds
# Source this file in build scripts to ensure consistency

# Debian version
export DEBIAN_VERSION="trixie"
export DEBIAN_VERSION_NUMBER="13"

# Debian cloud image URLs
export DEBIAN_CLOUD_IMAGE_BASE="https://cloud.debian.org/images/cloud/${DEBIAN_VERSION}/latest"
export DEBIAN_CLOUD_IMAGE_URL="${DEBIAN_CLOUD_IMAGE_BASE}/debian-${DEBIAN_VERSION_NUMBER}-genericcloud-amd64.qcow2"
export DEBIAN_CLOUD_IMAGE_CHECKSUM="file:${DEBIAN_CLOUD_IMAGE_BASE}/SHA512SUMS"

# AWS AMI (Debian official)
export DEBIAN_AWS_OWNER="136693071363"  # Debian's AWS account
export DEBIAN_AWS_AMI_NAME="debian-${DEBIAN_VERSION_NUMBER}-amd64-*"

# Package versions (if pinning is needed)
export PYTHON_VERSION="3.11"
export GIT_VERSION="latest"

# Build defaults
export DEFAULT_BUILD_MEMORY="2048"
export DEFAULT_BUILD_CPUS="2"

# Build and deployment disk sizes
# These should be kept in sync with packer-local/variables.pkr.hcl and deploy-local/deploy.sh
export DEFAULT_SOURCE_IMAGE_DISK_SIZE="10G"  # Temp disk for cloud image during Packer build
export DEFAULT_EFI_DISK_SIZE="2G"             # Final /boot/efi disk (created during deployment)
export DEFAULT_LVM_DISK_SIZE="10G"            # Final LVM root disk (build and deployment)

# Output
echo "Loaded VM Builder versions:"
echo "  Debian: ${DEBIAN_VERSION} (${DEBIAN_VERSION_NUMBER})"
echo "  Cloud Image: ${DEBIAN_CLOUD_IMAGE_URL}"
