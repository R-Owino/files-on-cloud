#!/bin/bash
# Import pre-existing AWS resources into Terraform state.
# Idempotent - silently skips resources not in AWS or already managed.

set -uo pipefail

TF="terraform -chdir=${1:-infra}"
P="filesoncloud"

import() {
  $TF import "$1" "$2" 2>/dev/null || true
}

lookup() {
  local val
  val=$("$@" 2>/dev/null) || true
  [[ -n "$val" && "$val" != "None" ]] && echo "$val"
}

echo "## IAM roles ##"
import "module.api-gateway.aws_iam_role.apilogs"                     "api-gateway-logs-role"
import "module.lambda.aws_iam_role.lambda_role"                       "${P}-lambda-role"
import "module.secrets-manager.aws_iam_role.secrets_access_role"      "${P}-secrets-access-role"
import "module.vpc.aws_iam_role.nat_instance_role[0]"                 "${P}-nat-instance-role"
import "module.ecs.aws_iam_role.ecs_execution_role"                   "${P}-ecs-execution-role"
import "module.ecs.aws_iam_role.ecs_task_role"                        "${P}-ecs-task-role"

echo "## IAM instance profile ##"
import "module.vpc.aws_iam_instance_profile.nat_instance_profile[0]" "${P}-nat-instance-profile"

echo "## DynamoDB tables ##"
import "module.dynamodb.aws_dynamodb_table.documents_metadata" "documents-metadata"
import "module.dynamodb.aws_dynamodb_table.userdata"           "userdata"

echo "## Lambda functions ##"
import "module.lambda.aws_lambda_function.userdata"                    "${P}-userdata-prod"
import "module.lambda.aws_lambda_function.upload_file_metadata"        "${P}-upload-prod"
import "module.lambda.aws_lambda_function.fetch_file_metadata"         "${P}-fetch-file-metadata-prod"
import "module.lambda.aws_lambda_function.delete_file"                 "${P}-delete-prod"

echo "## ECR repositories ##"
import "module.ecr.aws_ecr_repository.filesoncloud_app"   "filesoncloud-app"
import "module.ecr.aws_ecr_repository.filesoncloud_redis" "filesoncloud-redis"

echo "## Secrets Manager ##"
SM_ARN=$(lookup aws secretsmanager describe-secret \
  --secret-id "${P}-app-secrets" --query 'ARN' --output text)
[ -n "${SM_ARN:-}" ] && import \
  "module.secrets-manager.aws_secretsmanager_secret.app_secrets" "$SM_ARN"

echo "## Lambda permissions ##"
import "module.api-gateway.aws_lambda_permission.file_metadata"  "${P}-fetch-file-metadata-prod/AllowExecutionFromAPIGateway"
import "module.api-gateway.aws_lambda_permission.delete_lambda"  "${P}-delete-prod/AllowExecutionFromAPIGateway"
import "module.s3.aws_lambda_permission.upload_metadata_lambda"  "${P}-upload-prod/AllowS3Invoke"
import "module.cognito.aws_lambda_permission.allow_cognito"      "${P}-userdata-prod/AllowCognitoInvoke"

echo "## CloudFront ##"
OAC_ID=$(lookup aws cloudfront list-origin-access-controls \
  --query "OriginAccessControlList.Items[?Name=='${P}-s3-oac'].Id|[0]" --output text)
[ -n "${OAC_ID:-}" ] && import \
  "module.cloudfront.aws_cloudfront_origin_access_control.s3_oac" "$OAC_ID"

PK_ID=$(lookup aws cloudfront list-public-keys \
  --query "PublicKeyList.Items[?Name=='${P}-cloudfront-key'].Id|[0]" --output text)
[ -n "${PK_ID:-}" ] && import \
  "module.cloudfront.aws_cloudfront_public_key.files_key" "$PK_ID"

KG_ID=$(lookup aws cloudfront list-key-groups \
  --query "KeyGroupList.Items[?KeyGroup.KeyGroupConfig.Name=='${P}-key-group'].KeyGroup.Id|[0]" --output text)
[ -n "${KG_ID:-}" ] && import \
  "module.cloudfront.aws_cloudfront_key_group.files_key_group" "$KG_ID"

echo "## API Gateway stage ##"
API_ID=$(lookup aws apigateway get-rest-apis \
  --query "items[?name=='${P}-prod-rest-api'].id|[0]" --output text)
[ -n "${API_ID:-}" ] && import \
  "module.api-gateway.aws_api_gateway_stage.files" "${API_ID}/prod"

echo "## ALB target group ##"
TG_ARN=$(lookup aws elbv2 describe-target-groups --names "${P}-tg" \
  --query "TargetGroups[0].TargetGroupArn" --output text)
[ -n "${TG_ARN:-}" ] && import "module.alb.aws_lb_target_group.app" "$TG_ARN"

echo "## VPC endpoints ##"
VPC_ID=$(lookup aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=${P}-vpc" \
  --query "Vpcs[0].VpcId" --output text)

if [ -n "${VPC_ID:-}" ]; then
  vpc_ep() {
    local tf_name="$1" svc="$2"
    EP_ID=$(lookup aws ec2 describe-vpc-endpoints \
      --filters "Name=service-name,Values=com.amazonaws.${AWS_REGION}.${svc}" \
                "Name=vpc-id,Values=${VPC_ID}" \
                "Name=state,Values=available" \
      --query "VpcEndpoints[0].VpcEndpointId" --output text)
    [ -n "${EP_ID:-}" ] && import "module.vpc.aws_vpc_endpoint.${tf_name}" "$EP_ID"
  }

  vpc_ep secretsmanager  secretsmanager
  vpc_ep ssm             ssm
  vpc_ep ecr_api         ecr.api
  vpc_ep ecr_dkr         ecr.dkr
  vpc_ep logs            logs
  vpc_ep apigateway      execute-api
  vpc_ep s3              s3
  vpc_ep dynamodb        dynamodb
fi

echo "## Done ##"
