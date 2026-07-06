# Deploy Local - Local KVM Deployment

Deploy Packer-built images to local KVM/libvirt using virt-install.

> **See [../README.md](../README.md#local-build--deploy) for prerequisites and getting started guide.**

## Usage

### Basic Deployment
```bash
sudo ./deploy.sh ../packer-local/output/debian13-local/debian13-local --ssh-key ~/.ssh/vm-dev.pub
```

### Command-Line Options

```bash
sudo ./deploy.sh IMAGE [OPTIONS]

Arguments:
  IMAGE               Path to image (without extension)

Options:
  --name NAME         VM name (default: debian13-vm)
  --memory MB         RAM in MB (default: 4096)
  --vcpus N           Number of vCPUs (default: 4)
  --ssh-key PATH      SSH public key file
  --hostname NAME     VM hostname (default: debian13-vm)
```

### Example with Custom Settings
```bash
sudo ./deploy.sh ../packer-local/output/debian13-local/debian13-local \
  --name my-dev-vm \
  --memory 8192 \
  --vcpus 8 \
  --ssh-key ~/.ssh/vm-dev.pub \
  --hostname my-dev-vm
```

## Deployment Process

1. Creates VM with 4 disks:
   - `/dev/vda` (2GB) - EFI boot partition
   - `/dev/vdb` (1MB) - BIOS boot (compatibility)
   - `/dev/vdc` (10GB) - LVM root volume
   - `/dev/vdd` (20GB) - Backup volume
2. Attaches cloud-init ISO with SSH keys and configuration
3. VM boots and cloud-init configures hostname/SSH/network
4. `lvm-migrate.service` runs automatically (migrates to LVM)
5. VM reboots into final LVM layout
6. Ready for use (~1-2 minutes total)

## Managing VMs

```bash
# List VMs
sudo virsh list --all

# Get IP address
sudo virsh domifaddr debian13-vm

# Connect to console
sudo virsh console debian13-vm

# Stop/start
sudo virsh shutdown debian13-vm
sudo virsh start debian13-vm

# Delete VM (including disks)
sudo virsh destroy debian13-vm
sudo virsh undefine debian13-vm --remove-all-storage
```
