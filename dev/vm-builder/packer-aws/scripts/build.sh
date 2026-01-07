#!/bin/bash

# Build Debian AMI for AWS deployment with LVM

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load central configuration
source "$PROJECT_DIR/../common/config/vm-sizes.sh"
source "$PROJECT_DIR/../common/config/optional-tools.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Packer AWS Build ===${NC}"
echo ""
echo "Configuration:"
echo "  AWS Region:        $AWS_REGION"
echo "  AWS Profile:       $AWS_PROFILE"
echo "  Build Instance:    $AWS_BUILD_INSTANCE_TYPE"
echo "  Root Volume:       ${AWS_ROOT_VOLUME_SIZE}GB ($AWS_VOLUME_TYPE) - for /boot/efi"
echo "  LVM Volume:        ${AWS_LVM_VOLUME_SIZE}GB ($AWS_VOLUME_TYPE) - for root filesystem"
echo "  Backup Volume:     ${AWS_BACKUP_VOLUME_SIZE}GB ($AWS_VOLUME_TYPE) - for /srv/backup"
echo ""
echo "Optional Tools:"
echo "  Miniconda:         $INSTALL_MINICONDA"
echo "  Restic:            $INSTALL_RESTIC"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v packer &> /dev/null; then
    echo -e "${RED}Error: packer not found${NC}"
    echo "Install: sudo apt install packer"
    exit 1
fi

if ! command -v ansible &> /dev/null; then
    echo -e "${RED}Error: ansible not found${NC}"
    echo "Install: sudo apt install ansible"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: aws CLI not found${NC}"
    echo "Install AWS CLI first"
    exit 1
fi

# Verify AWS credentials
echo -e "${YELLOW}Verifying AWS credentials...${NC}"
if ! aws sts get-caller-identity --profile "$AWS_PROFILE" &> /dev/null; then
    echo -e "${RED}Error: AWS credentials not configured or invalid${NC}"
    echo "Run: aws configure --profile $AWS_PROFILE"
    exit 1
fi

AWS_ACCOUNT=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)
AWS_USER=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Arn --output text)
echo -e "${GREEN}✓ Authenticated as: $AWS_USER${NC}"
echo -e "${GREEN}✓ Account: $AWS_ACCOUNT${NC}"
echo ""

# Change to project directory
cd "$PROJECT_DIR"

# Initialize Packer plugins if needed
if [ ! -d ".packer.d" ]; then
    echo -e "${YELLOW}Initializing Packer plugins...${NC}"
    packer init .
    echo ""
fi

# Validate Packer configuration
echo -e "${YELLOW}Validating Packer configuration...${NC}"
packer validate \
  -var "aws_region=$AWS_REGION" \
  -var "aws_profile=$AWS_PROFILE" \
  -var "build_instance_type=$AWS_BUILD_INSTANCE_TYPE" \
  -var "root_volume_size=$AWS_ROOT_VOLUME_SIZE" \
  -var "lvm_volume_size=$AWS_LVM_VOLUME_SIZE" \
  -var "backup_volume_size=$AWS_BACKUP_VOLUME_SIZE" \
  -var "volume_type=$AWS_VOLUME_TYPE" \
  .
  
echo -e "${GREEN}✓ Configuration valid${NC}"
echo ""

# Build
echo -e "${YELLOW}Starting AMI build...${NC}"
echo -e "${BLUE}This will:${NC}"
echo "  1. Launch temporary EC2 instance ($AWS_BUILD_INSTANCE_TYPE)"
echo "  2. Attach three EBS volumes (${AWS_ROOT_VOLUME_SIZE}GB + ${AWS_LVM_VOLUME_SIZE}GB + ${AWS_BACKUP_VOLUME_SIZE}GB)"
echo "  3. Run Ansible provisioning (base, development)"
echo "  4. Set up LVM and migrate root filesystem"
echo "  5. Create AMI and terminate build instance"
echo ""
echo -e "${YELLOW}Note: This will incur AWS charges (minimal for build instance time)${NC}"
echo ""

# Prompt for confirmation
read -p "Continue with build? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Build cancelled"
    exit 0
fi

packer build \
  -var "aws_region=$AWS_REGION" \
  -var "aws_profile=$AWS_PROFILE" \
  -var "build_instance_type=$AWS_BUILD_INSTANCE_TYPE" \
  -var "root_volume_size=$AWS_ROOT_VOLUME_SIZE" \
  -var "lvm_volume_size=$AWS_LVM_VOLUME_SIZE" \
  -var "backup_volume_size=$AWS_BACKUP_VOLUME_SIZE" \
  -var "volume_type=$AWS_VOLUME_TYPE" \
  .

echo ""
echo -e "${GREEN}=== AMI Build Complete ===${NC}"
echo ""

# Parse manifest for AMI ID
if [ -f "output/manifest.json" ]; then
    AMI_ID=$(jq -r '.builds[0].artifact_id' output/manifest.json | cut -d':' -f2)
    echo -e "${GREEN}AMI Created: $AMI_ID${NC}"
    echo ""
    echo "View in AWS Console:"
    echo "  https://$AWS_REGION.console.aws.amazon.com/ec2/home?region=$AWS_REGION#Images:visibility=owned-by-me"
    echo ""
    echo "Next steps:"
    echo "  Deploy: cd ../deploy-aws && terraform init && terraform apply -var ami_id=$AMI_ID"
fi
echo ""
