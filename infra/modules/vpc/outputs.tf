output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.filesoncloud_vpc.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.filesoncloud_vpc.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "nat_type" {
  description = "Type of NAT being used"
  value       = var.use_nat_gateway ? "NAT Gateway" : "NAT Instance"
}

output "nat_instance_id" {
  description = "ID of the NAT instance (if using NAT instance)"
  value       = var.use_nat_gateway ? null : aws_instance.nat_instance[0].id
}
