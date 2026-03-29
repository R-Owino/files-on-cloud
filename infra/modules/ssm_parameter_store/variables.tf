variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  type        = string
}

variable "cognito_client_id" {
  description = "Cognito Client ID"
  type        = string
}

variable "api_gateway_fetch_metadata_url" {
  description = "API Gateway fetch metadata URL"
  type        = string
}

variable "api_gateway_delete_url" {
  description = "API Gateway delete URL"
  type        = string
}

variable "s3_bucket_name" {
  description = "S3 bucket name"
  type        = string
}

variable "documents_table_name" {
  description = "Documents DynamoDB table name"
  type        = string
}

variable "userdata_table_name" {
  description = "Userdata DynamoDB table name"
  type        = string
}

variable "cloudfront_domain" {
  description = "CloudFront domain"
  type        = string
}

variable "cloudfront_public_key_id" {
  description = "CloudFront public key ID"
  type        = string
}

variable "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  type        = string
}

variable "redis_host" {
  description = "Redis host"
  type        = string
  default     = "redis"
}

variable "redis_ecs" {
  description = "Redis ECS host"
  type        = string
  default     = "localhost"
}

variable "redis_port" {
  description = "Redis port"
  type        = number
  default     = 6379
}
