/* CloudFront distribution with S3 as origin */

resource "aws_cloudfront_origin_access_control" "s3_oac" {
  name                              = "${var.project_name}-s3-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_public_key" "files_key" {
  comment     = "Public key for CloudFront signed URLs"
  name        = "${var.project_name}-cloudfront-key"
  encoded_key = file("${path.module}/public_key.pem")
}

resource "aws_cloudfront_key_group" "files_key_group" {
  comment = "Key group for CloudFront signed URLs"
  name    = "${var.project_name}-key-group"
  items   = [aws_cloudfront_public_key.files_key.id]
}

resource "aws_cloudfront_distribution" "s3_distribution" {
  origin {
    domain_name              = var.s3_bucket_regional_domain_name
    origin_id                = "S3-${var.s3_bucket_id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.s3_oac.id
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = var.cloudfront_default_root_object

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${var.s3_bucket_id}"

    forwarded_values {
      query_string = true
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400

    trusted_key_groups = [aws_cloudfront_key_group.files_key_group.id]
  }

  price_class = "PriceClass_200"

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name        = "${var.project_name}-files",
    Environment = var.environment
  }
}
