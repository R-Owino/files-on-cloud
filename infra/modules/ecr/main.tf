# ECR repositories
resource "aws_ecr_repository" "filesoncloud_app" {
  name                 = var.app_repository_name
  image_tag_mutability = "MUTABLE"

  force_delete = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.project_name}-app-repository"
    Environment = var.environment
  }
}

resource "aws_ecr_repository" "filesoncloud_redis" {
  name                 = var.redis_repository_name
  image_tag_mutability = "MUTABLE"

  force_delete = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.project_name}-redis-repository"
    Environment = var.environment
  }
}

resource "aws_ecr_lifecycle_policy" "filesoncloud_app" {
  repository = aws_ecr_repository.filesoncloud_app.id

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep latest tag"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["latest"]
          countType     = "sinceImagePushed"
          countUnit     = "days"
          countNumber   = 999
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep last 10 non-latest images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["main-"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 3
        description  = "Delete untagged images older than 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 4
        description  = "Keep last 10 test images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["test-"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
