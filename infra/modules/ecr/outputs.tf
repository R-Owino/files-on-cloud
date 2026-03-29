output "app_repository_url" {
  description = "Flask app ECR repository URL"
  value       = aws_ecr_repository.filesoncloud_app.repository_url
}

output "redis_repository_url" {
  description = "Redis ECR repository URL"
  value       = aws_ecr_repository.filesoncloud_redis.repository_url
}
