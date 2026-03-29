output "bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.files.bucket
}

output "bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.files.arn
}

output "bucket_id" {
  description = "ID of the S3 bucket"
  value       = aws_s3_bucket.files.id
}

output "s3_bucket_regional_domain_name" {
  description = "Regional domain name of the S3 bucket"
  value       = aws_s3_bucket.files.bucket_regional_domain_name
}
