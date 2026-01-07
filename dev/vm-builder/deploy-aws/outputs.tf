output "instance_id" {
  description = "The ID of the EC2 instance"
  value       = aws_instance.vm.id
}

output "instance_public_ip" {
  description = "The public IP address of the instance"
  value       = aws_instance.vm.public_ip
}

output "instance_private_ip" {
  description = "The private IP address of the instance"
  value       = aws_instance.vm.private_ip
}

output "ami_id" {
  description = "The AMI ID used for this instance"
  value       = aws_instance.vm.ami
}

output "instance_type" {
  description = "The instance type"
  value       = aws_instance.vm.instance_type
}

output "ssh_connection" {
  description = "SSH connection command"
  value       = "ssh admin@${aws_instance.vm.public_ip}"
}

output "security_group_id" {
  description = "The ID of the security group"
  value       = aws_security_group.vm_sg.id
}
