# Generate random values for secrets
resource "random_password" "flask_secret_key" {
  length  = 64
  special = true
}

resource "random_password" "redis_password" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "app_secrets" {
  name                    = "${var.project_name}-app-secrets"
  description             = "Application secrets for ${var.project_name}"
  recovery_window_in_days = var.recovery_window_days

  tags = {
    Name        = "${var.project_name}-app-secrets"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    SECRET_KEY     = random_password.flask_secret_key.result
    REDIS_PASSWORD = random_password.redis_password.result
  })
}

resource "aws_iam_role" "secrets_access_role" {
  name = "${var.project_name}-secrets-access-role"

  assume_role_policy = file("${path.module}/secrets-access-role.json")

  tags = {
    Name        = "${var.project_name}-secrets-access-role"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy" "secrets_access_policy" {
  name = "${var.project_name}-secrets-access-policy"
  role = aws_iam_role.secrets_access_role.id

  policy = templatefile("${path.module}/secrets-access-policy.json", {
    secrets_arn = aws_secretsmanager_secret.app_secrets.arn
  })
}
