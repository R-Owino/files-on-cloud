data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_vpc" "filesoncloud_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.project_name}-vpc"
    Environment = var.environment
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.filesoncloud_vpc.id

  tags = {
    Name        = "${var.project_name}-igw"
    Environment = var.environment
  }
}

resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.filesoncloud_vpc.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.project_name}-public-subnet-${count.index + 1}"
    Environment = var.environment
    Type        = "Public"
  }
}

resource "aws_subnet" "private" {
  count = 2

  vpc_id            = aws_vpc.filesoncloud_vpc.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name        = "${var.project_name}-private-subnet-${count.index + 1}"
    Environment = var.environment
    Type        = "Private"
  }
}

# ============================================================================
# NAT GATEWAY CONFIGURATION (Comment out when using NAT Instance)
# ============================================================================

/*
resource "aws_eip" "nat" {
  count = var.use_nat_gateway ? 2 : 0

  domain     = "vpc"
  depends_on = [aws_internet_gateway.igw]

  tags = {
    Name        = "${var.project_name}-nat-eip-${count.index + 1}"
    Environment = var.environment
  }
}

resource "aws_nat_gateway" "filesoncloud_nat" {
  count = var.use_nat_gateway ? 2 : 0

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  depends_on    = [aws_internet_gateway.igw]

  tags = {
    Name        = "${var.project_name}-nat-gateway-${count.index + 1}"
    Environment = var.environment
  }
}
*/

# ============================================================================
# NAT INSTANCE CONFIGURATION (Comment out when using NAT Gateway)
# ============================================================================

# Security group for NAT instance
resource "aws_security_group" "nat_instance" {
  count = var.use_nat_gateway ? 0 : 1

  name_prefix = "${var.project_name}-nat-instance-"
  vpc_id      = aws_vpc.filesoncloud_vpc.id

  # SSH access (restrict to your IP in production)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP from private subnets
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  # HTTPS from private subnets
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  # All traffic from private subnets
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-nat-instance-sg"
    Environment = var.environment
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_instance" "nat_instance" {
  count = var.use_nat_gateway ? 0 : 1

  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = "t3.nano"
  subnet_id                   = aws_subnet.public[0].id
  vpc_security_group_ids      = [aws_security_group.nat_instance[0].id]
  associate_public_ip_address = true
  source_dest_check           = false
  iam_instance_profile        = aws_iam_instance_profile.nat_instance_profile[0].name
  key_name                    = "filesoncloud-nat-key"

  user_data = templatefile("${path.module}/nat_instance_userdata.sh", {
    vpc_cidr = var.vpc_cidr
  })

  tags = {
    Name        = "${var.project_name}-nat-instance"
    Environment = var.environment
  }

  lifecycle {
    ignore_changes = [ami]
  }
}

# IAM role for NAT instance
resource "aws_iam_role" "nat_instance_role" {
  count = var.use_nat_gateway ? 0 : 1

  name = "${var.project_name}-nat-instance-role"

  assume_role_policy = file("${path.module}/nat-instance-assume-role-policy.json")

  tags = {
    Name        = "${var.project_name}-nat-instance-role"
    Environment = var.environment
  }
}

resource "aws_iam_instance_profile" "nat_instance_profile" {
  count = var.use_nat_gateway ? 0 : 1

  name = "${var.project_name}-nat-instance-profile"
  role = aws_iam_role.nat_instance_role[0].name
}

# ============================================================================
# VPC ENDPOINTS
# ============================================================================

# Security group for VPC endpoints
resource "aws_security_group" "vpc_endpoints" {
  name_prefix = "${var.project_name}-vpc-endpoints-"
  vpc_id      = aws_vpc.filesoncloud_vpc.id

  # HTTPS from VPC
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-vpc-endpoints-sg"
    Environment = var.environment
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Secrets Manager VPC endpoint
resource "aws_vpc_endpoint" "secretsmanager" {
  vpc_id              = aws_vpc.filesoncloud_vpc.id
  service_name        = "com.amazonaws.${var.aws_region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-secretsmanager-endpoint"
    Environment = var.environment
  }
}

# Parameter Store VPC endpoint
resource "aws_vpc_endpoint" "ssm" {
  vpc_id              = aws_vpc.filesoncloud_vpc.id
  service_name        = "com.amazonaws.${var.aws_region}.ssm"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-ssm-endpoint"
    Environment = var.environment
  }
}

# ECR API VPC endpoint
resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.filesoncloud_vpc.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-ecr-api-endpoint"
    Environment = var.environment
  }
}

# ECR DKR VPC endpoint
resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.filesoncloud_vpc.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-ecr-dkr-endpoint"
    Environment = var.environment
  }
}

# CloudWatch Logs VPC endpoint
resource "aws_vpc_endpoint" "logs" {
  vpc_id              = aws_vpc.filesoncloud_vpc.id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-logs-endpoint"
    Environment = var.environment
  }
}

# API Gateway VPC Endpoint
resource "aws_vpc_endpoint" "apigateway" {
  vpc_id              = aws_vpc.filesoncloud_vpc.id
  service_name        = "com.amazonaws.${var.aws_region}.execute-api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-apigateway-endpoint"
    Environment = var.environment
  }
}

# S3 Gateway endpoint for ECR
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.filesoncloud_vpc.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = aws_route_table.private[*].id

  tags = {
    Name        = "${var.project_name}-s3-endpoint"
    Environment = var.environment
  }
}

# DynamoDB Gateway endpoint
resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = aws_vpc.filesoncloud_vpc.id
  service_name      = "com.amazonaws.${var.aws_region}.dynamodb"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = aws_route_table.private[*].id

  tags = {
    Name        = "${var.project_name}-dynamodb-endpoint"
    Environment = var.environment
  }
}

# ============================================================================
# ROUTE TABLES
# ============================================================================

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.filesoncloud_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name        = "${var.project_name}-public-rt"
    Environment = var.environment
  }
}

# separate route tables for each private subnet
resource "aws_route_table" "private" {
  count = 2

  vpc_id = aws_vpc.filesoncloud_vpc.id

  # route for NAT gateway
  dynamic "route" {
    for_each = var.use_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.filesoncloud_nat[count.index].id
    }
  }

  # route for NAT instance
  dynamic "route" {
    for_each = var.use_nat_gateway ? [] : [1]
    content {
      cidr_block           = "0.0.0.0/0"
      network_interface_id = aws_instance.nat_instance[0].primary_network_interface_id
    }
  }

  tags = {
    Name        = "${var.project_name}-private-rt"
    Environment = var.environment
  }
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}
