# Packer Local - Build Images for Local KVM

Builds Debian VM images for local KVM/libvirt deployment using Packer + Ansible.

> **See [../README.md](../README.md#local-build--deploy) for prerequisites and getting started guide.**

## Build Options

### Basic Build
```bash
./scripts/build.sh
```

### With Optional Tools
```bash
INSTALL_MINICONDA=true INSTALL_RESTIC=true ./scripts/build.sh
```

### Configuration
Edit [../common/config/vm-sizes.sh](../common/config/vm-sizes.sh) for disk sizes.  
Edit [../common/config/optional-tools.sh](../common/config/optional-tools.sh) for default tool flags.

## Output

After successful build (~10-20 minutes):
```
output/debian13-local/
├── debian13-local        # Boot disk image
├── debian13-local-lvm    # LVM root disk image
└── debian13-local-backup # Backup disk image
```

## What Gets Installed

- **Ansible roles**: base, development, lvm-migration, optional-tools (see [../common/README.md](../common/README.md))
- **LVM migration service**: Runs on first boot to migrate root to LVM
- **Optional tools**: Miniconda and/or restic (if enabled)

## Files

```
packer-local/
├── debian-cloud.pkr.hcl           # Main Packer template
├── variables.pkr.hcl              # Variable definitions
├── scripts/build.sh               # Build wrapper script
└── ansible/
    └── roles/lvm-migration/       # LVM migration service and scripts
```

Shared Ansible roles in [../common/ansible/roles/](../common/ansible/roles/)
