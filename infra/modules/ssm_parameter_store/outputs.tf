output "parameter_names" {
  description = "List of parameter names"
  value       = [for param in aws_ssm_parameter.app_config : param.name]
}
