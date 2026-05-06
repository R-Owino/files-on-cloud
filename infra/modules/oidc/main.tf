data "aws_caller_identity" "current" {}

data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github.certificates[0].sha1_fingerprint]

  tags = {
    Name        = "${var.project_name}-github-oidc-provider"
    Environment = var.environment
  }
}

resource "aws_iam_role" "github_oidc" {
  name = "${var.project_name}-oidc"

  assume_role_policy = templatefile("${path.module}/oidc-assume-role-policy.json", {
    oidc_provider_arn = aws_iam_openid_connect_provider.github.arn
    github_org        = var.github_org
  })

  tags = {
    Name        = "${var.project_name}-oidc-role"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "github_oidc_admin" {
  role       = aws_iam_role.github_oidc.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}
