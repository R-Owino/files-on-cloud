# The infrastructure

Terraform infrastructure for FilesOnCloud. The stack is split into two layers with separate state files so that long-lived resources that the CI pipeline depends on are never accidentally destroyed alongside the application infrastructure.

## Two-layer architecture

```
infra/
├── persistent/     # Layer 1 - ECR repos, OIDC provider/role. Apply once; rarely changes.
└── (root)          # Layer 2 - everything else: VPC, ECS, ALB, Lambda, S3, etc.
```

### Persistent layer (`infra/persistent/`)

Contains only the resources that the CI/CD pipeline needs to exist **before** it can run:

- **ECR repositories** (`filesoncloud-app`, `filesoncloud-redis`) - the build job pushes images here before Terraform deploys ECS
- **GitHub Actions OIDC provider + role** - the role the pipeline assumes via OIDC to authenticate with AWS

State key: `filesoncloud/persistent.tfstate`

Import blocks in `main.tf` make this layer idempotent - if state is ever lost, the next apply adopts the existing resources instead of failing.

### Ephemeral layer (`infra/` root)

The full application stack. Reads ECR URLs from the persistent layer's remote state via `data "terraform_remote_state"`.

State key: `filesoncloud/terraform.state`

## Module overview

| Module | What it provisions |
|---|---|
| `acm` | ACM certificate + Route 53 DNS validation records |
| `alb` | Application Load Balancer, HTTPS/HTTP listeners, target group |
| `api-gateway` | REST API, Cognito authorizer, metadata and delete methods, CORS, CloudWatch logging |
| `cloudfront` | Distribution with S3 origin, OAC, public key, trusted key group for signed URLs |
| `cognito` | User pool, user pool client, post-confirmation Lambda trigger |
| `dynamodb` | `documents-metadata` table (file metadata) and `userdata` table |
| `ecr` | ECR repositories with lifecycle policies (used from persistent layer) |
| `ecs` | ECS cluster (Fargate Spot), task definition (Flask + Redis sidecar), service |
| `lambda` | 4 functions: userdata (Cognito trigger), upload metadata (S3 trigger), fetch metadata (API Gateway), delete file (API Gateway); shared layer with PyJWT + requests |
| `oidc` | GitHub Actions OIDC identity provider and IAM role (used from persistent layer) |
| `route53` | Hosted zone, A record pointing to ALB, cert validation CNAME records |
| `s3` | Files bucket with accelerated transfer, versioning, lifecycle, CloudFront bucket policy, logging bucket |
| `secrets-manager` | `filesoncloud-app-secrets` secret holding generated `SECRET_KEY` and `REDIS_PASSWORD` |
| `ssm-parameter-store` | All app config parameters under `/filesoncloud/*` (Cognito IDs, API Gateway URLs, CloudFront domain/keys, DynamoDB table names, Redis config) |
| `vpc` | VPC, public/private subnets, IGW, NAT instance (t3.nano), route tables, security groups, VPC Interface endpoints for ECR/Secrets Manager/SSM/CloudWatch |

**NAT instance vs NAT Gateway** - a t3.nano EC2 instance running IP masquerading is used instead of a NAT Gateway to keep costs down. The tradeoff is single-AZ egress and no SLA on the NAT path.

## Remote state backend

Both layers share the same S3 bucket (created by `bootstrap/`) but use different state keys. The bucket has versioning enabled if state is ever corrupted or accidentally deleted, previous versions can be restored.

## First-time setup

### 1. Create the state bucket

```bash
cd infra/bootstrap
terraform init
terraform apply
# Note the bucket name from the output
```

Update `infra/backend.tf` and `infra/persistent/backend.tf` with the bucket name.

### 2. Generate CloudFront key pair

```bash
openssl genrsa -out api/v1/routes/private_key.pem 2048
openssl rsa -pubout -in api/v1/routes/private_key.pem -out infra/modules/cloudfront/public_key.pem
```

The private key goes in `api/v1/routes/` (not committed). The public key is read by Terraform at apply time.

### 3. Add GitHub Actions secrets

In the repository under **Settings → Secrets and Variables → Actions**:

| Secret | Value |
|---|---|
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID |
| `AWS_REGION` | e.g. `us-west-2` |
| `PRIVATE_KEY` | Full contents of `api/v1/routes/private_key.pem` |

### 4. Apply the persistent layer locally

The OIDC role must exist before the pipeline can authenticate with AWS. Apply once from your local machine with IAM user credentials:

```bash
cd infra/persistent
terraform init
terraform apply
```

After this, all future runs go through the CI pipeline.

### 5. Configure domain name servers

Before pushing for the first time, Route 53 needs to be authoritative for your domain so that ACM can validate the certificate. Run a targeted apply to create the hosted zone:

```bash
cd infra
terraform init
terraform apply -target=module.route53
```

Then copy the four NS record values from the Route 53 console into your domain registrar's nameserver settings and wait for propagation:

```bash
dig your-domain-name NS   # should return Route 53 nameservers
```

Once propagation is complete, push to `main` - the CI pipeline will handle everything from here.

## Deploying

Every push to `main` triggers the full pipeline:

1. **bootstrap-persistent** - applies `infra/persistent/`, adopting existing ECR repos and OIDC resources via import blocks
2. **build** - builds and pushes Docker images to ECR
3. **test** - runs the pytest suite inside the Docker test image (moto, no live AWS)
4. **deploy-infrastructure** (main branch only):
   - Stage 1: creates ACM cert + Route 53 DNS validation records, waits for cert to be `ISSUED`
   - Stage 2: full `terraform apply` - VPC, ALB, ECS, Lambda, API Gateway, CloudFront, etc.
5. **deploy-application** - updates the ECS service with the new image tag

## Tearing down

```bash
# Local development with Docker Compose
docker compose down   # terraform destroy runs automatically on container stop

# Production (destroys everything except the persistent layer and state bucket)
cd infra
terraform destroy
```

To also remove the persistent layer:

```bash
cd infra/persistent
terraform destroy
```

The state bucket and bootstrap resources are not managed by these workspaces and must be removed manually if no longer needed.
