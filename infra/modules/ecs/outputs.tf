output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.filesoncloud_ecs.name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.filesoncloud.name
}

output "ecs_task_definition_family" {
  description = "Name of the ECS task definition"
  value       = aws_ecs_task_definition.filesoncloud.family
}
