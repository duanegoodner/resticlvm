terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

# Data source to get default VPC if using default
data "aws_vpc" "default" {
  count   = var.use_default_vpc ? 1 : 0
  default = true
}

# Data source to get default subnet if using default VPC
data "aws_subnets" "default" {
  count = var.use_default_vpc ? 1 : 0
  
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default[0].id]
  }
}

# Security Group for SSH access
resource "aws_security_group" "vm_sg" {
  name_prefix = "${var.instance_name}-sg-"
  description = "Security group for ${var.instance_name}"
  vpc_id      = var.use_default_vpc ? data.aws_vpc.default[0].id : var.vpc_id

  # SSH access
  ingress {
    description = "SSH from allowed CIDRs"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.ssh_allowed_cidrs
  }

  # Allow all outbound traffic
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.instance_name}-sg"
    Environment = var.environment
  }

  lifecycle {
    create_before_destroy = true
  }
}

# EC2 Instance
resource "aws_instance" "vm" {
  ami           = var.ami_id
  instance_type = var.instance_type
  key_name      = var.ssh_key_name
  
  subnet_id              = var.use_default_vpc ? data.aws_subnets.default[0].ids[0] : var.subnet_id
  vpc_security_group_ids = [aws_security_group.vm_sg.id]
  
  # The AMI already has the volumes configured (8GB root + 10GB LVM)
  # No need to override block device mappings unless customizing
  
  tags = {
    Name        = var.instance_name
    Environment = var.environment
    OS          = "Debian 13"
    LVM         = "true"
    ManagedBy   = "Terraform"
  }

  # Ensure instance is stopped gracefully
  lifecycle {
    ignore_changes = [ami]  # Don't replace instance if AMI is updated
  }
}
