# defines outputs that will be displayed after terraform apply

output "aws_region" {
  description = "Region where the resources have been provisioned"
  value       = var.aws_region
}

output "cognito_user_pool_id" {
  description = "ID of the Cognito user pool"
  value       = module.cognito.userpool_id
}

output "cognito_user_pool_client_id" {
  description = "ID of the Cognito user pool client"
  value       = module.cognito.userpool_client_id
}

output "api_gateway_fetch_metadata_url" {
  description = "Invoke URL for fetching file metadata"
  value       = module.api-gateway.fetch_metadata_url
}

output "api_gateway_delete_url" {
  description = "Invoke URL for deleting files"
  value       = module.api-gateway.delete_url
}

output "s3_bucket_name" {
  description = "Name of the bucket where files are stored"
  value       = module.s3.bucket_name
}

output "documents_dynamodb_table_name" {
  description = "Name of DynamoDB table holding the files metadata"
  value       = module.dynamodb.documents_metadata_table_name
}

output "userdata_dynamodb_table_name" {
  description = "Name of DynamoDB table holding user data"
  value       = module.dynamodb.userdata_table_name
}

output "cloudfront_domain_name" {
  description = "CloudFront domain name"
  value       = module.cloudfront.cloudfront_domain_name
}

output "cloudfront_public_key_id" {
  description = "ID for the CloudFront public key"
  value       = module.cloudfront.cloudfront_public_key_id
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = module.cloudfront.cloudfront_distribution_id
}

output "app_repository_url" {
  description = "Flask app ECR repository URL"
  value       = module.ecr.app_repository_url
}

output "redis_repository_url" {
  description = "Redis ECR repository URL"
  value       = module.ecr.redis_repository_url
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.ecs.ecs_cluster_name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = module.ecs.ecs_service_name
}

output "ecs_task_definition_family" {
  description = "Name of the ECS task definition"
  value       = module.ecs.ecs_task_definition_family
}

output "secret_name" {
  description = "Name of the secrets manager secret"
  value       = module.secrets-manager.secret_name
}
