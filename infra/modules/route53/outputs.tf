output "hosted_zone_id" {
  description = "The hosted zone ID"
  value       = aws_route53_zone.filesoncloud_site.zone_id
}

output "name_servers" {
  description = "The name servers for the hosted zone"
  value       = aws_route53_zone.filesoncloud_site.name_servers
}

output "domain_name" {
  description = "The domain name"
  value       = aws_route53_zone.filesoncloud_site.name
}
