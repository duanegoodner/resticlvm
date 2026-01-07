packer {
  required_version = ">= 1.8.0"
  
  required_plugins {
    amazon = {
      version = "~> 1"
      source  = "github.com/hashicorp/amazon"
    }
    ansible = {
      version = "~> 1"
      source  = "github.com/hashicorp/ansible"
    }
  }
}

source "amazon-ebs" "debian_aws" {
  # AWS Authentication
  profile = var.aws_profile
  region  = var.aws_region
  
  # Source AMI (Official Debian 13)
  source_ami_filter {
    filters = {
      name                = var.source_ami_name_filter
      root-device-type    = "ebs"
      virtualization-type = "hvm"
      architecture        = "x86_64"
    }
    owners      = [var.source_ami_owner]
    most_recent = true
  }
  
  # Build Instance
  instance_type = var.build_instance_type
  ssh_username  = var.ssh_username
  
  # EBS Volumes Configuration
  # During build, we create three volumes:
  #   /dev/xvda - Root volume (must be >= source AMI, will become /boot/efi after migration)
  #   /dev/xvdf - LVM volume (will become root filesystem)
  #   /dev/xvdg - Backup volume (will become /srv/backup)
  
  # Root volume (must be >= source AMI size, Debian 13 = 8GB)
  launch_block_device_mappings {
    device_name           = "/dev/xvda"
    volume_size           = var.root_volume_size
    volume_type           = var.volume_type
    delete_on_termination = true
  }
  
  # LVM volume (for root filesystem)
  launch_block_device_mappings {
    device_name           = "/dev/xvdf"
    volume_size           = var.lvm_volume_size
    volume_type           = var.volume_type
    delete_on_termination = true
  }
  
  # Backup volume (for /srv/backup)
  launch_block_device_mappings {
    device_name           = "/dev/xvdg"
    volume_size           = var.backup_volume_size
    volume_type           = var.volume_type
    delete_on_termination = true
  }
  
  # AMI Configuration
  ami_name        = "${var.ami_name_prefix}-{{timestamp}}"
  ami_description = "Debian 13 with LVM root filesystem and backup volume (built by Packer)"
  
  tags = var.ami_tags
  
  # Ensure all volumes are included in the final AMI
  ami_block_device_mappings {
    device_name           = "/dev/xvda"
    volume_size           = var.root_volume_size
    volume_type           = var.volume_type
    delete_on_termination = true
  }
  
  ami_block_device_mappings {
    device_name           = "/dev/xvdf"
    volume_size           = var.lvm_volume_size
    volume_type           = var.volume_type
    delete_on_termination = true
  }
  
  ami_block_device_mappings {
    device_name           = "/dev/xvdg"
    volume_size           = var.backup_volume_size
    volume_type           = var.volume_type
    delete_on_termination = true
  }
}

build {
  sources = ["source.amazon-ebs.debian_aws"]
  
  # Wait for cloud-init and system to stabilize
  provisioner "shell" {
    inline = [
      "echo 'Waiting for cloud-init to complete...'",
      "cloud-init status --wait || true",
      "echo 'Waiting for system to stabilize...'",
      "sleep 30",
      "echo 'Ensuring no package managers are running...'",
      "while sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do sleep 2; done",
      "while sudo fuser /var/lib/apt/lists/lock >/dev/null 2>&1; do sleep 2; done",
      "echo 'System ready for provisioning'"
    ]
  }
  
  # Install LVM tools and prepare system
  provisioner "shell" {
    inline = [
      "echo 'Installing LVM tools...'",
      "sudo apt-get update",
      "sudo apt-get install -y lvm2 rsync"
    ]
  }
  
  # Common provisioning (base system, development tools)
  provisioner "ansible" {
    playbook_file = "${path.root}/../common/ansible/playbook.yml"
    user          = var.ssh_username
    extra_arguments = [
      "--extra-vars", "ansible_python_interpreter=/usr/bin/python3",
      "--extra-vars", "platform=${var.platform}",
      "--extra-vars", "enable_development=${var.enable_development}"
    ]
  }
  
  # Set up LVM and migrate root filesystem
  # This is AWS-specific and happens during build (not post-deploy like local)
  provisioner "shell" {
    environment_vars = [
      "LVM_LV_ROOT_SIZE=8G"
    ]
    scripts = [
      "${path.root}/scripts/setup-lvm.sh",
      "${path.root}/scripts/migrate-root-to-lvm.sh"
    ]
  }
  
  # Final cleanup before creating AMI
  provisioner "shell" {
    inline = [
      "echo 'Final cleanup...'",
      "sudo apt-get clean",
      "sudo rm -rf /tmp/*",
      "sudo rm -rf /var/tmp/*",
      # Clear cloud-init so it runs fresh on new instances (keep it enabled for AWS)
      "sudo cloud-init clean --logs",
      # Ensure cloud-init is NOT disabled (critical for AWS)
      "sudo rm -f /etc/cloud/cloud-init.disabled",
      "sudo rm -f /etc/cloud/cloud.cfg.d/99-disable-cloud-init.cfg",
      # Ensure cloud-init services are enabled
      "sudo systemctl enable cloud-init-local.service || true",
      "sudo systemctl enable cloud-init.service || true",
      "sudo systemctl enable cloud-config.service || true",
      "sudo systemctl enable cloud-final.service || true",
      # Clear SSH host keys so they regenerate
      "sudo rm -f /etc/ssh/ssh_host_*",
      # Clear bash history
      "sudo rm -f /root/.bash_history",
      "rm -f ~/.bash_history",
      "echo 'AMI build cleanup complete'"
    ]
  }
  
  post-processor "manifest" {
    output     = "${path.root}/output/manifest.json"
    strip_path = true
  }
}
