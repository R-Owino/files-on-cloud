output "certificate_arn" {
  description = "The ARN of the SSL certificate"
  value       = aws_acm_certificate.filesoncloud_cert.arn
}

output "certificate_domain_name" {
  description = "The domain name of the certificate"
  value       = aws_acm_certificate.filesoncloud_cert.domain_name
}
