# Deploy AWS - EC2 Instance Deployment

Terraform configuration for deploying EC2 instances from custom Debian AMI with LVM.

> **See [../README.md](../README.md#aws-build--deploy) for prerequisites and getting started guide.**

## Prerequisites

- AWS CLI configured with credentials
- Terraform installed (version >= 1.0)
- SSH key pair created in AWS
- Custom AMI built using [../packer-aws/](../packer-aws/)

## Configuration

1. **Copy example configuration**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit terraform.tfvars**:
   ```hcl
   ami_id       = "ami-0f7356d10733466d8"  # From packer-aws build output
   ssh_key_name = "my-debian-key"          # Your AWS SSH key name
   ```

3. **Optional settings**:
   ```hcl
   instance_name     = "debian13-dev-vm"
   instance_type     = "t3.small"
   aws_region        = "us-west-2"
   ssh_allowed_cidrs = ["1.2.3.4/32"]     # Restrict SSH to your IP
   ```

## Deployment

```bash
# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Deploy instance
terraform apply

# View outputs
terraform output
```

## Connect to Instance

```bash
# Get connection command
terraform output ssh_connection

# Connect
ssh -i ~/.ssh/my-debian-key.pem debian@<public-ip>
```

## Verify LVM Configuration

```bash
# Check disk layout
lsblk

# Expected output:
# xvda              8GB  /boot/efi
# xvdf             10GB  vg0-lv_root (8GB used, 2GB free in VG)
# xvdg             20GB  vg1-lv_backup

# Check volume groups
sudo vgdisplay
```

## Instance Management

```bash
# Stop instance (stops compute charges)
aws ec2 stop-instances --instance-ids $(terraform output -raw instance_id)

# Start instance
aws ec2 start-instances --instance-ids $(terraform output -raw instance_id)

# Destroy instance (deletes everything)
terraform destroy
```

## Estimated Costs (us-west-2)

- **t3.small**: ~$15/month running continuously
- **EBS volumes**: ~$1.50/month (2GB + 10GB + 20GB)
- **Total**: ~$16.50/month when running

**Tip**: Stop instance when not in use to avoid compute charges.

## Key Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ami_id` | Custom Debian AMI ID | Yes |
| `ssh_key_name` | AWS SSH key pair name | Yes |
| `instance_name` | Name tag for instance (default: debian13-vm) | No |
| `instance_type` | EC2 instance type (default: t3.small) | No |
| `aws_region` | AWS region (default: us-west-2) | No |
| `ssh_allowed_cidrs` | CIDR blocks for SSH (default: 0.0.0.0/0) | No |

See [terraform.tfvars.example](terraform.tfvars.example) for all options.
