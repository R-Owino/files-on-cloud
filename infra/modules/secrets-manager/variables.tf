variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "recovery_window_days" {
  description = "Number of days for secret recovery window"
  type        = number
  default     = 7
}
