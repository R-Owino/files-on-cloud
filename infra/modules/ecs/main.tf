# ECS cluster

resource "aws_ecs_cluster" "filesoncloud_ecs" {
  name = "${var.project_name}-ecs-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "${var.project_name}-ecs-cluster"
    Environment = var.environment
  }
}

resource "aws_ecs_cluster_capacity_providers" "capacity_provider" {
  cluster_name = aws_ecs_cluster.filesoncloud_ecs.name

  capacity_providers = ["FARGATE_SPOT"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE_SPOT"
  }
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-ecs-logs"
    Environment = var.environment
  }
}

# Security Group for ECS tasks
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "Allow inbound access from the ALB only"
  vpc_id      = var.vpc_id

  ingress {
    protocol        = "tcp"
    from_port       = var.container_port
    to_port         = var.container_port
    security_groups = [var.alb_security_group_id]
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-ecs-tasks-sg"
    Environment = var.environment
  }
}

# ECS task definition
resource "aws_ecs_task_definition" "filesoncloud" {
  family                   = "${var.project_name}-ecs-task"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.fargate_cpu
  memory                   = var.fargate_memory

  container_definitions = jsonencode([
    # Redis container
    {
      name   = "${var.project_name}-redis-container"
      image  = var.redis_image_uri
      memory = 256
      portMappings = [
        {
          containerPort = 6379
          hostPort      = 6379
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "AWS_SECRET_NAME"
          value = var.secrets_name
        },
        {
          name  = "ENVIRONMENT"
          value = "prod"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "redis"
        }
      }
      essential = true
      healthCheck = {
        command     = ["CMD-SHELL", "redis-cli ping"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    },

    # Flask app container
    {
      name   = "${var.project_name}-app-container"
      image  = var.flask_image_uri
      memory = 768
      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "AWS_SECRET_NAME"
          value = var.secrets_name
        },
        {
          name  = "ENVIRONMENT"
          value = "prod"
        }
      ]
      secrets = [
        {
          name      = "REDIS_PASSWORD"
          valueFrom = "${var.secrets_arn}:REDIS_PASSWORD::"
        },
        {
          name      = "SECRET_KEY"
          valueFrom = "${var.secrets_arn}:SECRET_KEY::"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "app"
        }
      }
      essential = true
      dependsOn = [
        {
          containerName = "${var.project_name}-redis-container"
          condition     = "HEALTHY"
        }
      ]
      healthCheck = {
        command     = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/health/liveness', timeout=3)"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Name        = "${var.project_name}-task-definition"
    Environment = var.environment
  }
}

# ECS Service
resource "aws_ecs_service" "filesoncloud" {
  name            = "${var.project_name}-ecs-service"
  cluster         = aws_ecs_cluster.filesoncloud_ecs.id
  task_definition = aws_ecs_task_definition.filesoncloud.arn
  desired_count   = var.desired_count

  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 100
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "${var.project_name}-app-container"
    container_port   = var.container_port
  }

  depends_on             = [aws_iam_role_policy.ecs_execution_policy, var.target_group_arn]
  enable_execute_command = true
}

# ECS task execution role
resource "aws_iam_role" "ecs_execution_role" {
  name               = "${var.project_name}-ecs-execution-role"
  assume_role_policy = file("${path.module}/ecs-assume-role-policy.json")

  tags = {
    Name        = "${var.project_name}-ecs-execution-role"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy" "ecs_execution_policy" {
  name   = "${var.project_name}-ecs-execution-policy"
  role   = aws_iam_role.ecs_execution_role.id
  policy = file("${path.module}/ecs-execution-policy.json")
}

resource "aws_iam_role_policy" "ecs_execution_secrets_policy" {
  name = "${var.project_name}-ecs-execution-secrets-policy"
  role = aws_iam_role.ecs_execution_role.id

  policy = templatefile("${path.module}/ecs-secrets-policy.json", {
    secrets_arn = var.secrets_arn
  })
}

# ECS task role
resource "aws_iam_role" "ecs_task_role" {
  name               = "${var.project_name}-ecs-task-role"
  assume_role_policy = file("${path.module}/ecs-assume-role-policy.json")

  tags = {
    Name        = "${var.project_name}-ecs-execution-role"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy" "ecs_task_policy" {
  name = "${var.project_name}-ecs-task-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = templatefile("${path.module}/ecs-task-policy.json", {
    s3_bucket_arn               = var.s3_bucket_arn
    documents_table_arn         = var.documents_table_arn
    userdata_table_arn          = var.userdata_table_arn
    cloudfront_distribution_arn = var.cloudfront_distribution_arn
    cognito_userpool_arn        = var.cognito_userpool_arn
  })
}

resource "aws_iam_role_policy" "ecs_task_parameter_store_policy" {
  name = "${var.project_name}-ecs-task-parameter-store-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = templatefile("${path.module}/parameter-store-policy.json", {
    project_name = var.project_name
    aws_region   = var.aws_region
  })
}

resource "aws_iam_role_policy" "ecs_task_secrets_policy" {
  name = "${var.project_name}-ecs-task-secrets-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = templatefile("${path.module}/ecs-secrets-policy.json", {
    secrets_arn = var.secrets_arn
  })
}
