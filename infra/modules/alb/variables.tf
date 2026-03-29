variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment (dev/prod)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs"
  type        = list(string)
}

variable "target_port" {
  description = "Port for the target group"
  type        = number
  default     = 5000
}

variable "target_protocol" {
  description = "Protocol for the target group"
  type        = string
  default     = "HTTP"
}

variable "health_check_path" {
  description = "Health check path"
  type        = string
  default     = "/health/liveness"
}

variable "health_check_healthy_threshold" {
  description = "Number of consecutive health checks successes required"
  type        = number
  default     = 2
}

variable "health_check_unhealthy_threshold" {
  description = "Number of consecutive health check failures required"
  type        = number
  default     = 3
}

variable "health_check_timeout" {
  description = "Amount of time to wait when receiving a response from the health check"
  type        = number
  default     = 10
}

variable "health_check_interval" {
  description = "Approximate amount of time between health checks"
  type        = number
  default     = 30
}

variable "health_check_matcher" {
  description = "Response codes to use when checking for a healthy responses"
  type        = string
  default     = "200"
}

variable "enable_deletion_protection" {
  description = "If true, deletion of the load balancer will be disabled via the AWS API"
  type        = bool
  default     = false
}

variable "certificate_arn" {
  description = "ARN of the SSL certificate for HTTPS listener"
  type        = string
}
