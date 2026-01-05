variable "vm_name" {
  type    = string
  default = "debian13-local"
}

variable "headless" {
  type    = bool
  default = true
  description = "Run QEMU in headless mode (no GUI window)"
}

# Build resources (for the VM during build, not final VM)
variable "build_memory" {
  type    = number
  default = 2048
  description = "RAM in MB for build VM"
}

variable "build_cpus" {
  type    = number
  default = 2
  description = "vCPUs for build VM"
}

# Disk configuration
# During Packer build, three disks are created:
#   1. source_image_disk - resized cloud image (temporary, used during build)
#   2. lvm_disk - will become the final LVM root volume
#   3. backup_disk - will become the backup LVM volume at /srv/backup
# During deployment, deploy-local creates:
#   1. Fresh disk from Packer output image
#   2. efi_disk - final /boot/efi partition  
#   3. lvm_disk - final LVM root (size should match build)
#   4. backup_disk - final backup LVM (size should match build)
# After LVM migration, the original image disk is cleaned up

variable "source_image_disk_size" {
  type    = string
  default = "10G"
  description = "Size for source cloud image disk (must be >= cloud image size, typically 2G minimum)"
}

variable "lvm_disk_size" {
  type    = string
  default = "10G"
  description = "Size of LVM disk for root filesystem (both build and deployment should use same size)"
}

variable "backup_disk_size" {
  type    = string
  default = "20G"
  description = "Size of backup LVM disk for /srv/backup (both build and deployment should use same size)"
}

variable "data_lv_disk_size" {
  type    = string
  default = "5G"
  description = "Size of additional LVM disk for /srv/data_lv (for testing non-root LVM backups)"
}

variable "data_standard_disk_size" {
  type    = string
  default = "5G"
  description = "Size of standard partition disk for /srv/data_standard_partition (for testing standard path backups)"
}

# Debian cloud image source
variable "debian_version" {
  type    = string
  default = "trixie"
  description = "Debian version codename (trixie = Debian 13)"
}

variable "cloud_image_url" {
  type    = string
  default = "https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2"
  description = "URL to Debian genericcloud image"
}

variable "cloud_image_checksum" {
  type    = string
  default = "file:https://cloud.debian.org/images/cloud/trixie/latest/SHA512SUMS"
  description = "Checksum for cloud image verification"
}

# Output
variable "output_dir" {
  type    = string
  default = "output/debian13-local"
}

# SSH credentials for provisioning
variable "ssh_username" {
  type    = string
  default = "debian"
  description = "Default user in Debian cloud images"
}

variable "ssh_password" {
  type    = string
  default = "debian"
  description = "Temporary password for provisioning (will be changed by Ansible)"
}

# Platform and provisioning options
variable "platform" {
  type    = string
  default = "local"
  description = "Deployment platform: local, aws, gcp, azure"
}

variable "enable_lvm_migration" {
  type    = bool
  default = true
  description = "Enable LVM migration service (local KVM specific)"
}

variable "enable_development" {
  type    = bool
  default = true
  description = "Install development tools and utilities"
}
