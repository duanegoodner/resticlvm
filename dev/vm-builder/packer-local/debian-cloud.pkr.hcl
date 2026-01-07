packer {
  required_version = ">= 1.8.0"
  
  required_plugins {
    qemu = {
      version = "~> 1"
      source  = "github.com/hashicorp/qemu"
    }
    ansible = {
      version = "~> 1"
      source  = "github.com/hashicorp/ansible"
    }
  }
}

source "qemu" "debian_local" {
  # VM Settings
  vm_name          = var.vm_name
  headless         = var.headless
  accelerator      = "kvm"
  
  # Resources (for build VM)
  memory           = var.build_memory
  cpus             = var.build_cpus
  
  # Source cloud image disk
  # This disk holds the base Debian cloud image and is used during build.
  # It must be >= the cloud image size (typically 2GB).
  # In deployed VMs, this becomes a temporary disk that gets cleaned up after LVM migration.
  disk_image       = true
  iso_url          = var.cloud_image_url
  iso_checksum     = var.cloud_image_checksum
  disk_size        = var.source_image_disk_size
  disk_interface   = "virtio"
  disk_cache       = "writeback"
  disk_discard     = "unmap"
  format           = "qcow2"
  
  # Additional disks for LVM and backup
  # First disk becomes the final root filesystem after LVM migration.
  # Second disk becomes the backup volume at /srv/backup.
  # Sizes should match what deploy-local will use.
  disk_additional_size = [var.lvm_disk_size, var.backup_disk_size]
  
  # Network
  net_device       = "virtio-net"
  
  # Cloud-init for initial access
  # We use NoCloud datasource with simple user-data
  cd_files = [
    "${path.root}/cloud-init-bootstrap/user-data",
    "${path.root}/cloud-init-bootstrap/meta-data"
  ]
  cd_label = "cidata"
  
  # SSH for provisioning
  ssh_username     = var.ssh_username
  ssh_password     = var.ssh_password
  ssh_timeout      = "30m"
  ssh_wait_timeout = "30m"
  ssh_handshake_attempts = 30
  ssh_keep_alive_interval = "5s"
  ssh_read_write_timeout = "5m"
  
  # Shutdown
  shutdown_command = "echo '${var.ssh_password}' | sudo -S shutdown -P now"
  
  # Output
  output_directory = var.output_dir
}

build {
  sources = ["source.qemu.debian_local"]
  
  # Wait for cloud-init to complete and system to stabilize
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
  
  # Provision using common Ansible playbook
  provisioner "ansible" {
    playbook_file = "${path.root}/../common/ansible/playbook.yml"
    user          = var.ssh_username
    extra_arguments = [
      "--extra-vars", "ansible_python_interpreter=/usr/bin/python3",
      "--extra-vars", "platform=${var.platform}",
      "--extra-vars", "enable_development=${var.enable_development}"
    ]
  }
  
  # Install LVM migration service (local-specific)
  # This runs AFTER common provisioning
  provisioner "ansible" {
    playbook_file   = "${path.root}/ansible/playbook-local.yml"
    user            = var.ssh_username
    extra_arguments = [
      "--extra-vars", "ansible_python_interpreter=/usr/bin/python3",
      "--extra-vars", "enable_lvm_migration=${var.enable_lvm_migration}"
    ]
  }
  
  # Cleanup before finalizing image
  provisioner "shell" {
    inline = [
      "echo 'Cleaning up...'",
      "sudo apt-get clean",
      "sudo rm -rf /tmp/*",
      "sudo rm -rf /var/tmp/*",
      # Clear cloud-init artifacts so it runs fresh on deployment (but keep it enabled)
      "sudo cloud-init clean --logs",
      # Ensure cloud-init is NOT disabled
      "sudo rm -f /etc/cloud/cloud-init.disabled",
      "sudo rm -f /etc/cloud/cloud.cfg.d/99-disable-cloud-init.cfg",
      # Ensure cloud-init services are enabled
      "sudo systemctl enable cloud-init-local.service || true",
      "sudo systemctl enable cloud-init.service || true",
      "sudo systemctl enable cloud-config.service || true",
      "sudo systemctl enable cloud-final.service || true",
      # Clear SSH keys so they regenerate on deployment
      "sudo rm -f /etc/ssh/ssh_host_*",
      # Clear hostname so it can be set on deployment
      "sudo truncate -s 0 /etc/hostname",
      "sudo sed -i '/127.0.1.1/d' /etc/hosts",
      # Clear bash history
      "sudo rm -f /root/.bash_history",
      "rm -f ~/.bash_history",
      "echo 'Build cleanup complete'"
    ]
  }
  
  post-processor "manifest" {
    output     = "${var.output_dir}/manifest.json"
    strip_path = true
  }
}
