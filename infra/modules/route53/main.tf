resource "aws_route53_zone" "filesoncloud_site" {
  name = var.domain_name

  tags = {
    Name        = "${var.project_name}-hosted-zone"
    Environment = var.environment
  }
}

resource "aws_route53_record" "ns_for_filesoncloud_site" {
  zone_id = aws_route53_zone.filesoncloud_site.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = true
  }

}

resource "aws_route53_record" "filesoncloud_www" {
  zone_id = aws_route53_zone.filesoncloud_site.zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = true
  }
}
