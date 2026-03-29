variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "aws_region" {
  description = "The AWS region in which resources will be created."
  type        = string
}

variable "environment" {
  description = "Environment (dev/prod)"
  type        = string
}

variable "dynamodb_userdata_table_name" {
  description = "Name of the DynamoDB table containing user data"
  type        = string
}

variable "dynamodb_userdata_table_arn" {
  description = "ARN of the DynamoDB userdata table"
  type        = string
}

variable "dynamodb_documents_metadata_table_name" {
  description = "Name of the DynamoDB table containing documents metadata"
  type        = string
}

variable "dynamodb_documents_metadata_table_arn" {
  description = "ARN of the DynamoDB documents table"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket used to store documents"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  type        = string
}

variable "userpool_id" {
  description = "ID of the Cognito user pool"
  type        = string
}
