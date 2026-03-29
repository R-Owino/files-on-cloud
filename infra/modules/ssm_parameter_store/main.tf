resource "aws_ssm_parameter" "app_config" {
  for_each = {
    "AWS_REGION"                         = var.aws_region
    "AWS_COGNITO_USER_POOL_ID"           = var.cognito_user_pool_id
    "AWS_COGNITO_CLIENT_ID"              = var.cognito_client_id
    "AWS_API_GATEWAY_FETCH_METADATA_URL" = var.api_gateway_fetch_metadata_url
    "AWS_API_GATEWAY_DELETE_URL"         = var.api_gateway_delete_url
    "S3_BUCKET_NAME"                     = var.s3_bucket_name
    "DOCUMENTS_DYNAMODB_TABLE_NAME"      = var.documents_table_name
    "USERDATA_DYNAMODB_TABLE_NAME"       = var.userdata_table_name
    "CLOUDFRONT_DOMAIN"                  = var.cloudfront_domain
    "CLOUDFRONT_PUBLIC_KEY_ID"           = var.cloudfront_public_key_id
    "CLOUDFRONT_DISTRIBUTION_ID"         = var.cloudfront_distribution_id
    "REDIS_HOST"                         = var.redis_host
    "REDIS_ECS"                          = var.redis_ecs
    "REDIS_PORT"                         = tostring(var.redis_port)
  }

  name      = "/${var.project_name}/${each.key}"
  type      = "String"
  value     = each.value
  overwrite = true

  tags = {
    Name        = "${var.project_name}-${each.key}"
    Environment = var.environment
  }
}
