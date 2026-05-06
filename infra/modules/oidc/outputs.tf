output "role_arn" {
  description = "ARN of the IAM role assumed by GitHub Actions"
  value       = aws_iam_role.github_oidc.arn
}

output "provider_arn" {
  description = "ARN of the GitHub Actions OIDC provider"
  value       = aws_iam_openid_connect_provider.github.arn
}
