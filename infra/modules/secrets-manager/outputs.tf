output "secret_arn" {
  description = "ARN of the secrets manager secret"
  value       = aws_secretsmanager_secret.app_secrets.arn
}

output "secret_name" {
  description = "Name of the secrets manager secret"
  value       = aws_secretsmanager_secret.app_secrets.name
}

output "secrets_access_role_arn" {
  description = "ARN of the IAM role for accessing secrets"
  value       = aws_iam_role.secrets_access_role.arn
}

output "flask_secret_key" {
  description = "Generated Flask secret key"
  value       = random_password.flask_secret_key.result
  sensitive   = true
}

output "redis_password" {
  description = "Generated Redis password"
  value       = random_password.redis_password.result
  sensitive   = true
}
