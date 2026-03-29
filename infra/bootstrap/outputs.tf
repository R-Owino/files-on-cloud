output "bucket_name" {
  description = "Name of the remote state S3 bucket"
  value       = aws_s3_bucket.terraform_state.bucket
}
