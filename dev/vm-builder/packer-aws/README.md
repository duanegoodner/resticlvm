# Packer AWS - Build AMIs for AWS EC2

Builds Debian 13 AMIs with LVM root filesystem for AWS EC2 deployment.

> **See [../README.md](../README.md#aws-build--deploy) for prerequisites and getting started guide.**

## Key Differences from Local

- **LVM Setup**: Configured during AMI build (not at instance launch)
- **Base Image**: Official Debian AMI from AWS Marketplace
- **Storage**: EBS volumes instead of qcow2 files
- **Output**: AMI registered in your AWS account

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
Edit [../common/config/vm-sizes.sh](../common/config/vm-sizes.sh) for EBS volume sizes.  
Edit [../common/config/optional-tools.sh](../common/config/optional-tools.sh) for default tool flags.

**Build time**: ~15-30 minutes  
**Build cost**: ~$0.02 (t3.small instance time)

## Output

After successful build:
```
AMI Created: ami-0abc123def456...
Region: us-west-2
```

View in AWS Console: EC2 → Images → AMIs (filter: Owned by me)

## Final Instance Layout

```
/dev/xvda1 (2GB)   → /boot/efi (EFI boot partition)
/dev/xvdf (10GB)   → Physical Volume
  └─ vg0           → Volume Group (with configurable free space)
     └─ lv_root    → / (root filesystem, size configured in vm-sizes.sh)
/dev/xvdg (20GB)   → Physical Volume
  └─ vg1           → Volume Group
     └─ lv_backup  → /srv/backup
```

**Important**: LVM is configured during build, not at instance launch.

## Files

```
packer-aws/
├── debian-aws.pkr.hcl           # Main Packer template
├── variables.pkr.hcl            # Variable definitions
├── scripts/
│   ├── build.sh                 # Build wrapper script
│   ├── setup-lvm.sh             # LVM setup during build
│   └── migrate-root-to-lvm.sh  # Root filesystem migration
└── output/
    └── manifest.json            # Build metadata (AMI ID, etc.)
```

Shared Ansible roles in [../common/ansible/roles/](../common/ansible/roles/)
