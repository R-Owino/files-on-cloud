
output "load_balancer_id" {
  description = "ID of the load balancer"
  value       = aws_lb.filesoncloud_ecs_lb.id
}
output "load_balancer_arn" {
  description = "ARN of the load balancer"
  value       = aws_lb.filesoncloud_ecs_lb.arn
}

output "load_balancer_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.filesoncloud_ecs_lb.dns_name
}

output "target_group_arn" {
  description = "ARN of the target group"
  value       = aws_lb_target_group.app.arn
}

output "security_group_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}

output "load_balancer_zone_id" {
  description = "Zone ID of the ALB"
  value       = aws_lb.filesoncloud_ecs_lb.zone_id
}
