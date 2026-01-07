# Common Configuration

Shared configuration and provisioning scripts used by both local and cloud deployments.

> **See [../README.md](../README.md) for complete getting started guide.**

## Structure

```
common/
├── ansible/                    # Ansible roles and playbooks
│   ├── playbook.yml           # Main playbook (platform-agnostic)
│   ├── ansible.cfg            # Ansible configuration
│   └── roles/
│       ├── base/              # Base system configuration
│       ├── development/       # Development tools
│       ├── lvm-migration/     # LVM migration service (local only)
│       └── optional-tools/    # Optional tools (miniconda, restic)
├── config/                    # Centralized configuration
│   ├── vm-sizes.sh            # Disk sizes for local and AWS
│   └── optional-tools.sh      # Optional tool installation flags
└── scripts/                   # Utility scripts
```

## Ansible Roles

### base
Cloud-agnostic base system configuration:
- Base packages (lvm2, rsync, vim, curl, etc.)
- SSH server configuration
- systemd-networkd fallback (if cloud-init fails)
- Timezone and GRUB console setup

### development
Development tools and environment:
- Build essentials (gcc, make, etc.)
- Version control (git, git-lfs)
- Python development (python3, pip, venv)
- Dev utilities (tmux, screen, jq, tree, strace)

### lvm-migration
First-boot LVM migration service (local VMs only):
- Migrates root filesystem from cloud image to LVM
- Creates vg0/lv_root on /dev/vdc (root)
- Creates vg1/lv_backup on /dev/vdd (backup)
- Runs once, then self-disables

### optional-tools
Optional development tools (controlled by environment variables):
- **Miniconda**: Installed to ~/miniconda3 when `INSTALL_MINICONDA=true`
- **Restic**: Installed via apt when `INSTALL_RESTIC=true`

## Configuration Files

### vm-sizes.sh
Centralized disk size configuration:
- `VM_LVM_DISK_SIZE`, `VM_LVM_LV_ROOT_SIZE` - Local VM sizes
- `VM_BACKUP_DISK_SIZE` - Backup volume size
- `AWS_LVM_VOLUME_SIZE`, `AWS_LVM_LV_ROOT_SIZE` - AWS EBS sizes
- `AWS_BACKUP_VOLUME_SIZE` - AWS backup volume

### optional-tools.sh
Optional tool installation flags:
- `INSTALL_MINICONDA` - Install miniconda (default: false)
- `INSTALL_RESTIC` - Install restic backup tool (default: false)

These files are sourced by build scripts in `packer-local/` and `packer-aws/`.
