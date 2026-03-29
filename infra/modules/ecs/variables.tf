variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment (dev/prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region to provision services"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of the private subnet IDs"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "ALB security group"
  type        = string
}

variable "target_group_arn" {
  description = "ARN of the target group"
  type        = string
}

variable "flask_image_uri" {
  description = "Flask Docker image to run in the ECS cluster"
  type        = string
}

variable "redis_image_uri" {
  description = "Redis Docker image to run in the ECS cluster"
  type        = string
}

variable "container_port" {
  description = "Port exposed by the docker image to redirect traffic to"
  type        = number
  default     = 5000
}

variable "fargate_cpu" {
  description = "Fargate instance CPU units to provision (1 vCPU = 1024 CPU units)"
  type        = string
  default     = "256"
}

variable "fargate_memory" {
  description = "Fargate instance memory to provision (in MiB)"
  type        = string
  default     = "1024"
}

variable "desired_count" {
  description = "Number of docker containers to run"
  type        = number
  default     = 1
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 7
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket holding the files"
  type        = string
}

variable "documents_table_arn" {
  description = "ARN of the Documents DynamoDB table"
  type        = string
}

variable "userdata_table_arn" {
  description = "ARN of the Userdata DynamoDB table"
  type        = string
}

variable "cognito_userpool_arn" {
  description = "ARN of the Cognito User Pool"
  type        = string
}

variable "cloudfront_distribution_arn" {
  description = "ARN of the CloudFront distribution"
  type        = string
}

variable "secrets_name" {
  description = "Name of the secrets manager secret"
  type        = string
}

variable "secrets_arn" {
  description = "ARN of the secrets manager secret"
  type        = string
}
