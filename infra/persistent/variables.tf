variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "filesoncloud"
}

variable "environment" {
  description = "Environment"
  type        = string
  default     = "prod"
}
