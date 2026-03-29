variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment (dev/prod)"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket used to store documents"
  type        = string
}

variable "s3_bucket_id" {
  description = "ID of the S3 bucket"
  type        = string
}

variable "s3_bucket_regional_domain_name" {
  description = "Regional domain name of the S3 bucket"
  type        = string
}

variable "cloudfront_default_root_object" {
  description = "Default root object for the cloudfront distribution"
  type        = string
  default     = "index.html"
}
