module "ecr" {
  source = "../modules/ecr"

  project_name = var.project_name
  environment  = var.environment
}

# Import blocks — idempotent: no-op when repos are already in state,
# auto-recover when state is lost but repos still exist in AWS.
import {
  to = module.ecr.aws_ecr_repository.filesoncloud_app
  id = "filesoncloud-app"
}

import {
  to = module.ecr.aws_ecr_repository.filesoncloud_redis
  id = "filesoncloud-redis"
}
