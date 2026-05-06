variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
}

variable "environment" {
  description = "Environment"
  type        = string
}

variable "github_org" {
  description = "GitHub username or organisation that owns the repository"
  type        = string
}
