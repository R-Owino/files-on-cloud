variable "project_name" {
  description = "The project name, which will be used as a prefix for remote state S3 bucket."
  type        = string
  default     = "filesoncloud"
}

variable "environment" {
  description = "Environment"
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "The AWS region in which remote S3 bucket will be created."
  type        = string
  default     = "us-west-2"
}
