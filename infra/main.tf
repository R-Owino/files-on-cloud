# main entry file for terraform modules

data "terraform_remote_state" "persistent" {
  backend = "s3"
  config = {
    bucket  = "filesoncloud-terraform-state-7byr6f"
    key     = "filesoncloud/persistent.tfstate"
    region  = var.aws_region
    encrypt = true
  }
}

module "acm" {
  source = "./modules/acm"

  domain_name    = var.domain_name
  project_name   = var.project_name
  environment    = var.environment
  hosted_zone_id = module.route53.hosted_zone_id
}

module "alb" {
  source = "./modules/alb"

  project_name      = var.project_name
  environment       = var.environment
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  certificate_arn   = module.acm.certificate_arn
}

module "api-gateway" {
  source = "./modules/api-gateway"

  aws_region                         = var.aws_region
  project_name                       = var.project_name
  environment                        = var.environment
  userpool_arn                       = module.cognito.userpool_arn
  file_metadata_arn                  = module.lambda.file_metadata_function_arn
  delete_lambda_arn                  = module.lambda.delete_function_arn
  file_metadata_invoke_arn           = module.lambda.file_metadata_invoke_arn
  delete_lambda_invoke_arn           = module.lambda.delete_lambda_invoke_arn
  file_metadata_lambda_function_name = module.lambda.file_metadata_function_name
  delete_lambda_function_name        = module.lambda.delete_lambda_function_name
}

module "cognito" {
  source = "./modules/cognito"

  project_name           = var.project_name
  environment            = var.environment
  userdata_function_arn  = module.lambda.userdata_function_arn
  userdata_function_name = module.lambda.userdata_function_name
  dynamodb_table_name    = var.userdata_table_name
}

module "cloudfront" {
  source = "./modules/cloudfront"

  project_name                   = var.project_name
  environment                    = var.environment
  s3_bucket_name                 = module.s3.bucket_name
  s3_bucket_id                   = module.s3.bucket_id
  s3_bucket_regional_domain_name = module.s3.s3_bucket_regional_domain_name
  cloudfront_default_root_object = "index.html"
}

module "dynamodb" {
  source = "./modules/dynamodb"

  project_name                  = var.project_name
  environment                   = var.environment
  userdata_table_name           = var.userdata_table_name
  documents_metadata_table_name = var.documents_metadata_table_name
}

module "ecs" {
  source = "./modules/ecs"

  project_name                = var.project_name
  environment                 = var.environment
  aws_region                  = var.aws_region
  vpc_id                      = module.vpc.vpc_id
  private_subnet_ids          = module.vpc.private_subnet_ids
  alb_security_group_id       = module.alb.security_group_id
  target_group_arn            = module.alb.target_group_arn
  flask_image_uri             = var.flask_image_uri != "" ? var.flask_image_uri : "${data.terraform_remote_state.persistent.outputs.app_repository_url}:latest"
  redis_image_uri             = var.redis_image_uri != "" ? var.redis_image_uri : "${data.terraform_remote_state.persistent.outputs.redis_repository_url}:latest"
  s3_bucket_arn               = module.s3.bucket_arn
  documents_table_arn         = module.dynamodb.documents_metadata_table_arn
  userdata_table_arn          = module.dynamodb.userdata_table_arn
  cloudfront_distribution_arn = module.cloudfront.cloudfront_distribution_arn
  cognito_userpool_arn        = module.cognito.userpool_arn
  secrets_name                = module.secrets-manager.secret_name
  secrets_arn                 = module.secrets-manager.secret_arn

  depends_on = [module.alb]
}

module "lambda" {
  source = "./modules/lambda"

  project_name                           = var.project_name
  aws_region                             = var.aws_region
  environment                            = var.environment
  dynamodb_userdata_table_name           = module.dynamodb.userdata_table_name
  dynamodb_userdata_table_arn            = module.dynamodb.userdata_table_arn
  dynamodb_documents_metadata_table_name = module.dynamodb.documents_metadata_table_name
  dynamodb_documents_metadata_table_arn  = module.dynamodb.documents_metadata_table_arn
  s3_bucket_name                         = module.s3.bucket_name
  s3_bucket_arn                          = module.s3.bucket_arn
  userpool_id                            = module.cognito.userpool_id
}

module "route53" {
  source = "./modules/route53"

  domain_name  = var.domain_name
  project_name = var.project_name
  environment  = var.environment
  alb_dns_name = module.alb.load_balancer_dns_name
  alb_zone_id  = module.alb.load_balancer_zone_id
}

module "s3" {
  source = "./modules/s3"

  project_name                  = var.project_name
  environment                   = var.environment
  upload_metadata_function_name = module.lambda.upload_metadata_function_name
  upload_metadata_function_arn  = module.lambda.upload_metadata_function_arn
}

resource "aws_s3_bucket_policy" "allow_cloudfront_access" {
  bucket = module.s3.bucket_id
  policy = templatefile("${path.module}/modules/s3/cloudfront-s3-policy.json", {
    bucket_arn                  = module.s3.bucket_arn
    cloudfront_distribution_arn = module.cloudfront.cloudfront_distribution_arn
  })

  depends_on = [module.s3, module.cloudfront]
}

module "ssm-parameter-store" {
  source = "./modules/ssm-parameter-store"

  project_name                   = var.project_name
  environment                    = var.environment
  aws_region                     = var.aws_region
  cognito_user_pool_id           = module.cognito.userpool_id
  cognito_client_id              = module.cognito.userpool_client_id
  api_gateway_fetch_metadata_url = module.api-gateway.fetch_metadata_url
  api_gateway_delete_url         = module.api-gateway.delete_url
  s3_bucket_name                 = module.s3.bucket_name
  documents_table_name           = module.dynamodb.documents_metadata_table_name
  userdata_table_name            = module.dynamodb.userdata_table_name
  cloudfront_domain              = module.cloudfront.cloudfront_domain_name
  cloudfront_public_key_id       = module.cloudfront.cloudfront_public_key_id
  cloudfront_distribution_id     = module.cloudfront.cloudfront_distribution_id
}

module "secrets-manager" {
  source = "./modules/secrets-manager"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
}

module "vpc" {
  source = "./modules/vpc"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
}
