data "aws_caller_identity" "current" {}

module "ecr" {
  source = "../modules/ecr"

  project_name = var.project_name
  environment  = var.environment
}

module "oidc" {
  source = "../modules/oidc"

  project_name = var.project_name
  environment  = var.environment
  github_org   = var.github_org
}

# Import blocks — idempotent: no-op when resources are already in state,
# auto-recover when state is lost but resources still exist in AWS.

import {
  to = module.ecr.aws_ecr_repository.filesoncloud_app
  id = "filesoncloud-app"
}

import {
  to = module.ecr.aws_ecr_repository.filesoncloud_redis
  id = "filesoncloud-redis"
}

import {
  to = module.oidc.aws_iam_openid_connect_provider.github
  id = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
}

import {
  to = module.oidc.aws_iam_role.github_oidc
  id = "${var.project_name}-oidc"
}
