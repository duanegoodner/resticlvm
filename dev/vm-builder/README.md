# VM Builder - Debian VMs with LVM Root

> **Note:** This directory was cloned from [https://github.com/duanegoodner/vm-builder](https://github.com/duanegoodner/vm-builder) at commit [6bdd04dc70f9c61dfec98fac3e4f26d484c208d8](https://github.com/duanegoodner/vm-builder/commit/6bdd04dc70f9c61dfec98fac3e4f26d484c208d8). The `.git/` directory and a top-level `archive/` directory were removed from the clone before adding to the ResticLVM repository. We aim to avoid editing the content of `dev/vm-builder/` directly (preferring to make changes in the original repository and re-clone), but cannot guarantee that no local edits have been made.

Build and deploy Debian VMs with LVM root filesystem for snapshot testing. Works for both local KVM and AWS.

## Quick Start

### Local

```bash
cd packer-local && ./scripts/build.sh
cd ../deploy-local && sudo ./deploy.sh ../packer-local/output/debian13-local/debian13-local --ssh-key ~/.ssh/vm-dev.pub
ssh -i ~/.ssh/vm-dev debian@<IP>
```

### AWS

```bash
cd packer-aws && ./scripts/build.sh
cd ../deploy-aws && terraform init && terraform apply
ssh -i ~/.ssh/your-key.pem debian@<PUBLIC_IP>
```

## Overview

This project creates Debian VMs with this filesystem layout:

```
NAME                    MAJ:MIN RM  SIZE RO TYPE MOUNTPOINTS
vda                     254:0    0    2G  0 disk 
└─vda1                  254:1    0    2G  0 part /boot/efi
vdb                     254:16   0   10G  0 disk 
├─vg0-lv_root           253:0    0    8G  0 lvm  /
└─(2G free in vg0)
vdc                     254:32   0   10G  0 disk 
└─vg1-lv_backup         253:1    0   10G  0 lvm  /srv/backup
vdd                     254:48   0    5G  0 disk 
├─vg2-lv_data           253:2    0    2G  0 lvm  /srv/data_lv
└─(3G free in vg2)
vde                     254:64   0    5G  0 disk 
└─vde1                  254:65   0    5G  0 part /srv/data_standard_partition
```

Perfect for:
- Testing LVM snapshot workflows
- Restic backup testing with LVM snapshots
- Development environments with snapshot capability
- Consistent VM images across local and cloud

---

## Getting Started

### Prerequisites

**Required:**
```bash
# Packer and Ansible
sudo apt install packer ansible

# For local builds: QEMU/KVM and libvirt
sudo apt install qemu-kvm libvirt-daemon-system virtinst cloud-image-utils
sudo usermod -a -G libvirt $USER
# Logout and login for group change to take effect

# For AWS builds: AWS CLI configured
aws configure  # Set up credentials, region, etc.
```

### Configuration

Optional tools and disk sizes are configured in `common/config/`:

**Optional Tools** ([common/config/optional-tools.sh](common/config/optional-tools.sh)):
```bash
export INSTALL_MINICONDA=false  # Set to true to include
export INSTALL_RESTIC=false     # Set to true to include
```

**Disk Sizes** ([common/config/vm-sizes.sh](common/config/vm-sizes.sh)):
```bash
# Local VMs
export VM_LVM_DISK_SIZE="10G"       # Physical disk for root
export VM_LVM_LV_ROOT_SIZE="8G"     # Root LV size (leaves 2G free in vg0)
export VM_BACKUP_DISK_SIZE="20G"    # Backup disk at /srv/backup

# AWS EC2
export AWS_LVM_VOLUME_SIZE="10"     # GB for root EBS volume
export AWS_LVM_LV_ROOT_SIZE="8"     # GB for root LV (leaves 2G free)
export AWS_BACKUP_VOLUME_SIZE="20"  # GB for backup EBS volume
```

### Local Build & Deploy

**1. Build Image**

```bash
cd packer-local

# Build with default settings
./scripts/build.sh

# OR build with optional tools
INSTALL_MINICONDA=true INSTALL_RESTIC=true ./scripts/build.sh
```

Output: `output/debian13-local/debian13-local` (plus 2 additional disk images)  
Time: ~10-20 minutes

**2. Deploy VM**

```bash
cd ../deploy-local

# Deploy with SSH key
sudo ./deploy.sh ../packer-local/output/debian13-local/debian13-local \
  --ssh-key ~/.ssh/vm-dev.pub

# OR with custom settings
sudo ./deploy.sh ../packer-local/output/debian13-local/debian13-local \
  --name my-vm \
  --memory 8192 \
  --vcpus 4 \
  --ssh-key ~/.ssh/vm-dev.pub
```

**3. Access VM**

Wait for LVM migration (~1-2 minutes):
- VM boots from cloud image
- cloud-init configures hostname/SSH/network
- LVM migration service runs automatically
- VM reboots into final LVM layout

```bash
# Get IP address
sudo virsh domifaddr debian13-vm

# SSH
ssh -i ~/.ssh/vm-dev debian@<IP>
```

Final disk layout:
- `/boot/efi` - 2GB EFI partition
- `/` - 8GB LVM (vg0-lv_root) with 2GB free in vg0
- `/srv/backup` - 10GB LVM (vg1-lv_backup)
- `/srv/data_lv` - 2GB LVM (vg2-lv_data) with 3GB free in vg2
- `/srv/data_standard_partition` - 5GB standard partition

### AWS Build & Deploy

**1. Build AMI**

```bash
cd packer-aws

# Build with default settings
./scripts/build.sh

# OR build with optional tools
INSTALL_MINICONDA=true INSTALL_RESTIC=true ./scripts/build.sh
```

Output: AMI in your AWS account (check output for AMI ID)  
Time: ~15-30 minutes  
Note: LVM migration happens during build (not at instance launch like local VMs)

**2. Deploy EC2 Instance**

```bash
cd ../deploy-aws

# Edit terraform.tfvars with your settings
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars  # Set ami_id, key_name, etc.

# Deploy
terraform init
terraform apply
```

**3. Access Instance**

```bash
# Get public IP from Terraform output
terraform output instance_public_ip

# SSH
ssh -i ~/.ssh/your-key.pem debian@<PUBLIC_IP>
```

Disk layout:
- `/boot/efi` - 8GB root volume
- `/` - 8GB LVM (vg0-lv_root) with 2GB free
- `/srv/backup` - 20GB LVM (vg1-lv_backup)

### Customization

**Adding Project-Specific Software**

Create custom Ansible roles in [common/ansible/roles/](common/ansible/roles/):

```bash
mkdir -p common/ansible/roles/my-app/tasks
cat > common/ansible/roles/my-app/tasks/main.yml << 'EOF'
---
- name: Install my application
  apt:
    name: my-package
    state: present
EOF
```

Then add to [common/ansible/playbook.yml](common/ansible/playbook.yml):
```yaml
roles:
  - role: my-app
    tags: ['my-app']
```

**Changing Disk Sizes**

Edit [common/config/vm-sizes.sh](common/config/vm-sizes.sh) and rebuild images.

**Cloud-init Customization**

For local deployments, edit [deploy-local/deploy.sh](deploy-local/deploy.sh) to modify the generated user-data.

---

## Architecture

### 3-Layer Approach

**Layer 1: Packer + Ansible (Build Time)**  
Purpose: Create reusable, configured VM images

- **Packer**: Orchestrates image building
- **Ansible**: System configuration (packages, services, LVM setup)
- Outputs: Platform-specific VM images ready for deployment

**Layer 2: Cloud-Init (Deployment Time)**  
Purpose: Runtime customization of deployed VMs

Handles:
- SSH keys
- Hostnames and networking
- User accounts
- Platform-specific initialization

NOT for:
- Package installation (too slow, use Packer)
- Complex filesystem operations (use Ansible + systemd service)

**Layer 3: Deploy Tools (Orchestration)**  
Purpose: Deploy images anywhere

- Local: `virt-install` (proven, reliable for KVM)
- Cloud: Terraform (AWS, GCP, Azure support)

### LVM Migration Strategy

The VM starts with a traditional root partition, then migrates to LVM on first boot:

1. **Packer Build**: Ansible installs `lvm-migrate.service` and migration script
2. **First Boot**: systemd service runs automatically before other services
3. **Migration**: Script creates LVM, copies root, updates GRUB/fstab
4. **Reboot**: System boots from LVM root
5. **Completion**: Service disables itself

**Why This Approach?**
- Works identically for local and cloud deployments
- Reliable: Service runs early, handles errors gracefully
- Cloud-compatible: Debian cloud images don't support LVM during initial setup
- Idempotent: Safe to run multiple times

### Project Structure

```
vm-builder/
├── common/                # Shared configuration and Ansible roles
│   ├── config/           # Centralized settings (vm-sizes.sh, optional-tools.sh)
│   └── ansible/          # Ansible playbook and roles
│       └── roles/
│           ├── base/
│           ├── development/
│           ├── lvm-migration/
│           └── optional-tools/
├── packer-local/         # Build images for local KVM
├── packer-aws/           # Build AMIs for AWS
├── deploy-local/         # Deploy to local KVM (virt-install)
├── deploy-aws/           # Deploy to AWS (Terraform)
└── archive/              # Previous approaches (preserved for reference)
```

### Key Design Principles

1. **Shared Configuration**: Ansible roles and config files used across all platforms
2. **Fast Deployment**: Heavy lifting done at build time, not deploy time
3. **Flexibility**: Easy to add new cloud providers or customize per project
4. **Consistency**: Same LVM setup and base configuration everywhere
5. **Clean Separation**: Build concerns vs deploy concerns properly separated
6. **Cloud-Native**: Uses genericcloud images as starting point for local and cloud

---
## Troubleshooting

### Build Issues

**Packer can't connect via SSH:**
- Check QEMU is working: `qemu-system-x86_64 --version`
- Verify KVM: `ls -la /dev/kvm`
- Check user in kvm group: `groups`

**Ansible provisioning fails:**
- Check ansible is installed: `ansible --version`
- Review packer output for specific error

### Deployment Issues

**VM doesn't start:**
- Check libvirt: `sudo systemctl status libvirtd`
- Review logs: `sudo journalctl -u libvirtd`

**cloud-init issues:**
```bash
# On VM
cloud-init status --long
journalctl -u cloud-init
```

**LVM migration doesn't run:**
- Connect to console: `virsh console <vm-name>`
- Check service: `sudo systemctl status lvm-migrate`
- View logs: `sudo journalctl -u lvm-migrate`

**Can't SSH to VM:**
- Check cloud-init: `virsh console <vm-name>` then `sudo cloud-init status --long`
- Verify network: `virsh net-list`
- Check if systemd-networkd fallback is active: `systemctl status systemd-networkd`

**Networking issues:**
```bash
# Check IP configuration
ip addr show

# View systemd-networkd status (fallback)
systemctl status systemd-networkd
```

---

## Why This Approach?

### vs Installing from ISO
- ❌ ISO install is slow (full OS install each time)
- ❌ Different starting point than cloud
- ✅ Cloud image is fast and consistent

### vs Configuring During Deployment
- ❌ Ansible during deployment is slow
- ❌ Need to manage Ansible in deployment environment
- ✅ Configuration baked into image = fast deployment

### vs Terraform for Local
- ❌ Terraform libvirt provider has stability issues
- ❌ Complex state management for simple VMs
- ✅ virt-install is proven and reliable for KVM

---

## Component Documentation

- [packer-local/README.md](packer-local/README.md) - Local image building details
- [packer-aws/README.md](packer-aws/README.md) - AWS AMI building details  
- [deploy-local/README.md](deploy-local/README.md) - Local deployment details
- [deploy-aws/README.md](deploy-aws/README.md) - AWS deployment details

---

## License

See [LICENSE](LICENSE)

## Archive

Previous approaches are preserved in [archive/](archive/):
- [archive/packer-ansible/](archive/packer-ansible/) - Original working approach (now evolved into packer-local)
- [archive/cloud-init/](archive/cloud-init/) - Early cloud-init attempt (LVM in runcmd - wrong layer)
- [archive/preseed-shell/](archive/preseed-shell/) - Preseed approach (can't extend to cloud)
- [archive/terraform-ansible/](archive/terraform-ansible/) - Early Terraform attempt
- [archive/terraform-ansible-new/](archive/terraform-ansible-new/) - Recent Terraform attempt (libvirt issues)

The current approach learned from all of these!

