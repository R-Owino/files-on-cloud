output "cloudfront_domain_name" {
  description = "CloudFront domain name"
  value       = aws_cloudfront_distribution.s3_distribution.domain_name
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.s3_distribution.id
}

output "cloudfront_distribution_arn" {
  description = "ARN of the CloudFront distribution"
  value       = aws_cloudfront_distribution.s3_distribution.arn
}

output "cloudfront_key_group_id" {
  description = "ID of the CloudFront key group"
  value       = aws_cloudfront_key_group.files_key_group.id
}

output "cloudfront_public_key_id" {
  description = "ID of the CloudFront public key"
  value       = aws_cloudfront_public_key.files_key.id
}

output "cloudfront_key_pair_id" {
  description = "The Key Pair ID for the CloudFront public key"
  value       = aws_cloudfront_public_key.files_key.caller_reference
}
