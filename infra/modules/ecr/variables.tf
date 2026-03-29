variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment (dev/prod)"
  type        = string
}

variable "app_repository_name" {
  description = "Name of the Flask app ECR repository"
  type        = string
  default     = "filesoncloud-app"
}

variable "redis_repository_name" {
  description = "Name of the Redis ECR repository"
  type        = string
  default     = "filesoncloud-redis"
}
