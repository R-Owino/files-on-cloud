variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "aws_region" {
  description = "The AWS region in which resources will be created."
  type        = string
}

variable "environment" {
  description = "Environment"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "use_nat_gateway" {
  description = "Set to true for NAT Gateway, false for NAT instance"
  type        = bool
  default     = false
}
