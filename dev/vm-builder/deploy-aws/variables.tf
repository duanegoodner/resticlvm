variable "ami_id" {
  type        = string
  description = "AMI ID to deploy (from packer-aws build)"
}

variable "instance_name" {
  type        = string
  default     = "debian13-vm"
  description = "Name tag for the EC2 instance"
}

variable "instance_type" {
  type        = string
  default     = "t3.small"
  description = "EC2 instance type"
}

variable "aws_region" {
  type        = string
  default     = "us-west-2"
  description = "AWS region for deployment"
}

variable "aws_profile" {
  type        = string
  default     = "default"
  description = "AWS CLI profile to use"
}

variable "ssh_key_name" {
  type        = string
  description = "Name of existing AWS EC2 key pair for SSH access"
}

variable "ssh_allowed_cidrs" {
  type        = list(string)
  default     = ["0.0.0.0/0"]
  description = "CIDR blocks allowed to SSH (default: anywhere - restrict for production!)"
}

variable "environment" {
  type        = string
  default     = "development"
  description = "Environment tag (development, staging, production)"
}

variable "use_default_vpc" {
  type        = bool
  default     = true
  description = "Use default VPC (true) or specify VPC/subnet IDs (false)"
}

variable "vpc_id" {
  type        = string
  default     = ""
  description = "VPC ID (only needed if use_default_vpc = false)"
}

variable "subnet_id" {
  type        = string
  default     = ""
  description = "Subnet ID (only needed if use_default_vpc = false)"
}
