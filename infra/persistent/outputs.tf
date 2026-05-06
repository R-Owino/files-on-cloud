output "app_repository_url" {
  description = "Flask app ECR repository URL"
  value       = module.ecr.app_repository_url
}

output "redis_repository_url" {
  description = "Redis ECR repository URL"
  value       = module.ecr.redis_repository_url
}

output "github_oidc_role_arn" {
  description = "ARN of the IAM role assumed by GitHub Actions"
  value       = module.oidc.role_arn
}
