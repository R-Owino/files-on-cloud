output "app_repository_url" {
  description = "Flask app ECR repository URL"
  value       = module.ecr.app_repository_url
}

output "redis_repository_url" {
  description = "Redis ECR repository URL"
  value       = module.ecr.redis_repository_url
}
