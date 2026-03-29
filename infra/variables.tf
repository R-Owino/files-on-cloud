# define and configure terraform variables

variable "aws_region" {
  description = "The AWS region in which resources will be created."
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "The project name, which will be used as a prefix for all resources."
  type        = string
  default     = "filesoncloud"
}

variable "userdata_table_name" {
  description = "Name of the DynamoDB table holding user information"
  type        = string
  default     = "userdata"
}

variable "documents_metadata_table_name" {
  description = "Name of the DynamoDB table holding file metadata"
  type        = string
  default     = "documents-metadata"
}

variable "domain_name" {
  description = "Custom domain name for the application"
  type        = string
  default     = "filesoncloud.site"
}

variable "flask_image_uri" {
  description = "Flask Docker image URI with tag for ECS deployment"
  type        = string
  default     = ""
}

variable "redis_image_uri" {
  description = "Redis Docker image URI with tag for ECS deployment"
  type        = string
  default     = ""
}
