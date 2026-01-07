variable "ami_name_prefix" {
  type    = string
  default = "debian-13-lvm"
  description = "Prefix for AMI name (timestamp will be appended)"
}

# AWS Configuration
variable "aws_region" {
  type    = string
  default = "us-west-2"
  description = "AWS region for building AMI"
}

variable "aws_profile" {
  type    = string
  default = "default"
  description = "AWS CLI profile to use for authentication"
}

# Build Instance Configuration
variable "build_instance_type" {
  type    = string
  default = "t3.small"
  description = "Instance type for Packer build (temporary)"
}

# Source AMI (Official Debian)
variable "source_ami_owner" {
  type    = string
  default = "136693071363"
  description = "AWS account ID for official Debian AMIs"
}

variable "source_ami_name_filter" {
  type    = string
  default = "debian-13-amd64-*"
  description = "Filter to find latest Debian 13 AMI"
}

# Disk Configuration for AWS EBS Volumes
# Three volumes will be created:
#   1. Root volume - must be >= source AMI size (Debian 13 = 8GB), becomes /boot/efi after migration
#   2. LVM volume - becomes root filesystem after LVM migration
#   3. Backup volume - becomes /srv/backup
variable "root_volume_size" {
  type    = number
  default = 8
  description = "Size in GB for root/boot volume (must be >= source AMI size, Debian 13 = 8GB)"
}

variable "lvm_volume_size" {
  type    = number
  default = 10
  description = "Size in GB for LVM root filesystem volume"
}

variable "backup_volume_size" {
  type    = number
  default = 20
  description = "Size in GB for backup LVM volume mounted at /srv/backup"
}

variable "volume_type" {
  type    = string
  default = "gp3"
  description = "EBS volume type (gp3 recommended for cost/performance)"
}

# SSH Configuration
variable "ssh_username" {
  type    = string
  default = "admin"
  description = "Default SSH user for Debian AMIs"
}

# Platform and provisioning options
variable "platform" {
  type    = string
  default = "aws"
  description = "Deployment platform identifier"
}

variable "enable_development" {
  type    = bool
  default = true
  description = "Install development tools and utilities"
}

# Tags
variable "ami_tags" {
  type = map(string)
  default = {
    Name        = "Debian 13 with LVM"
    OS          = "Debian"
    Version     = "13"
    BuildTool   = "Packer"
    Environment = "development"
  }
  description = "Tags to apply to the resulting AMI"
}
