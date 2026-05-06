#!/bin/bash
# Cleanup of orphaned AWS resources from the previous deployment.
#
# Intentionally excluded:
#   - ECR repos        (managed by persistent layer)
#   - ACM certificate  (already ISSUED, expensive to re-validate)
#   - Route53 zone     (NS records already configured at registrar)
#   - OIDC provider + role  (managed by persistent layer)

set -uo pipefail

REGION="us-west-2"
P="filesoncloud"
ENV="prod"

aws="aws --region $REGION"

echo "========================================"
echo " AWS Cleanup"
echo "========================================"

##### ECS #####
echo ""
echo "==> ECS"
$aws ecs update-service --cluster "${P}-ecs-cluster" \
  --service "${P}-ecs-service" --desired-count 0 2>/dev/null || true
$aws ecs delete-service --cluster "${P}-ecs-cluster" \
  --service "${P}-ecs-service" --force 2>/dev/null || true
$aws ecs delete-cluster --cluster "${P}-ecs-cluster" 2>/dev/null || true

##### ALB #####
echo ""
echo "==> ALB"
ALB_ARN=$($aws elbv2 describe-load-balancers --names "${P}-alb" \
  --query "LoadBalancers[0].LoadBalancerArn" --output text 2>/dev/null) || ALB_ARN=""
if [[ -n "$ALB_ARN" && "$ALB_ARN" != "None" ]]; then
  for arn in $($aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" \
    --query "Listeners[*].ListenerArn" --output text 2>/dev/null | tr '\t' ' '); do
    $aws elbv2 delete-listener --listener-arn "$arn" 2>/dev/null || true
  done
  $aws elbv2 delete-load-balancer --load-balancer-arn "$ALB_ARN" 2>/dev/null || true
  echo "  Waiting for ALB deletion..."
  $aws elbv2 wait load-balancers-deleted --load-balancer-arns "$ALB_ARN" 2>/dev/null || true
fi
TG_ARN=$($aws elbv2 describe-target-groups --names "${P}-tg" \
  --query "TargetGroups[0].TargetGroupArn" --output text 2>/dev/null) || TG_ARN=""
[[ -n "$TG_ARN" && "$TG_ARN" != "None" ]] && \
  $aws elbv2 delete-target-group --target-group-arn "$TG_ARN" 2>/dev/null || true

##### API GATEWAY #####
echo ""
echo "==> API Gateway"
API_ID=$($aws apigateway get-rest-apis \
  --query "items[?name=='${P}-${ENV}-rest-api'].id|[0]" --output text 2>/dev/null) || API_ID=""
[[ -n "$API_ID" && "$API_ID" != "None" ]] && \
  $aws apigateway delete-rest-api --rest-api-id "$API_ID" 2>/dev/null || true

##### LAMBDA #####
echo ""
echo "==> Lambda"
for fn in "${P}-userdata-${ENV}" "${P}-upload-${ENV}" \
          "${P}-fetch-file-metadata-${ENV}" "${P}-delete-${ENV}"; do
  $aws lambda delete-function --function-name "$fn" 2>/dev/null || true
done
LAYER_VERSIONS=$($aws lambda list-layer-versions \
  --layer-name "${P}-dependencies" \
  --query "LayerVersions[*].Version" --output text 2>/dev/null | tr '\t' ' ') || true
for v in $LAYER_VERSIONS; do
  $aws lambda delete-layer-version \
    --layer-name "${P}-dependencies" --version-number "$v" 2>/dev/null || true
done

##### COGNITO #####
echo ""
echo "==> Cognito"
POOL_ID=$($aws cognito-idp list-user-pools --max-results 20 \
  --query "UserPools[?Name=='${P}-${ENV}'].Id|[0]" --output text 2>/dev/null) || POOL_ID=""
if [[ -n "$POOL_ID" && "$POOL_ID" != "None" ]]; then
  for client in $($aws cognito-idp list-user-pool-clients --user-pool-id "$POOL_ID" \
    --query "UserPoolClients[*].ClientId" --output text 2>/dev/null | tr '\t' ' '); do
    $aws cognito-idp delete-user-pool-client \
      --user-pool-id "$POOL_ID" --client-id "$client" 2>/dev/null || true
  done
  $aws cognito-idp delete-user-pool --user-pool-id "$POOL_ID" 2>/dev/null || true
fi

##### CLOUDFRONT #####
echo ""
echo "==> CloudFront"
CF_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[?contains(DomainName,'${P}')]].Id|[0]" \
  --output text 2>/dev/null) || CF_ID=""
if [[ -n "$CF_ID" && "$CF_ID" != "None" ]]; then
  ENABLED=$(aws cloudfront get-distribution --id "$CF_ID" \
    --query "Distribution.DistributionConfig.Enabled" --output text)
  if [[ "$ENABLED" == "true" ]]; then
    echo "  Disabling CloudFront distribution $CF_ID..."
    CONFIG=$(aws cloudfront get-distribution-config --id "$CF_ID" --output json)
    ETAG=$(echo "$CONFIG" | python3 -c "import sys,json; print(json.load(sys.stdin)['ETag'])")
    DIST_CONFIG=$(echo "$CONFIG" | python3 -c "
import sys,json
d=json.load(sys.stdin); d['DistributionConfig']['Enabled']=False
print(json.dumps(d['DistributionConfig']))")
    aws cloudfront update-distribution --id "$CF_ID" \
      --if-match "$ETAG" --distribution-config "$DIST_CONFIG" > /dev/null
    echo "  Waiting for disable to propagate (~5 min)..."
    aws cloudfront wait distribution-deployed --id "$CF_ID"
  fi
  ETAG=$(aws cloudfront get-distribution --id "$CF_ID" --query "ETag" --output text)
  aws cloudfront delete-distribution --id "$CF_ID" --if-match "$ETAG" 2>/dev/null || true
fi

KG_ID=$(aws cloudfront list-key-groups \
  --query "KeyGroupList.Items[?KeyGroup.KeyGroupConfig.Name=='${P}-key-group'].KeyGroup.Id|[0]" \
  --output text 2>/dev/null) || KG_ID=""
if [[ -n "$KG_ID" && "$KG_ID" != "None" ]]; then
  KG_ETAG=$(aws cloudfront get-key-group --id "$KG_ID" --query "ETag" --output text)
  aws cloudfront delete-key-group --id "$KG_ID" --if-match "$KG_ETAG" 2>/dev/null || true
fi

PK_ID=$(aws cloudfront list-public-keys \
  --query "PublicKeyList.Items[?Name=='${P}-cloudfront-key'].Id|[0]" \
  --output text 2>/dev/null) || PK_ID=""
if [[ -n "$PK_ID" && "$PK_ID" != "None" ]]; then
  PK_ETAG=$(aws cloudfront get-public-key --id "$PK_ID" --query "ETag" --output text)
  aws cloudfront delete-public-key --id "$PK_ID" --if-match "$PK_ETAG" 2>/dev/null || true
fi

OAC_ID=$(aws cloudfront list-origin-access-controls \
  --query "OriginAccessControlList.Items[?Name=='${P}-s3-oac'].Id|[0]" \
  --output text 2>/dev/null) || OAC_ID=""
if [[ -n "$OAC_ID" && "$OAC_ID" != "None" ]]; then
  OAC_ETAG=$(aws cloudfront get-origin-access-control --id "$OAC_ID" --query "ETag" --output text)
  aws cloudfront delete-origin-access-control \
    --id "$OAC_ID" --if-match "$OAC_ETAG" 2>/dev/null || true
fi

##### VPC #####
echo ""
echo "==> VPC resources"
for VPC_ID in $($aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=${P}-vpc" \
  --query "Vpcs[*].VpcId" --output text 2>/dev/null | tr '\t' ' '); do
  echo "  Cleaning VPC $VPC_ID"

  EP_IDS=$($aws ec2 describe-vpc-endpoints \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=state,Values=available,pending" \
    --query "VpcEndpoints[*].VpcEndpointId" --output text 2>/dev/null | tr '\t' ' ')
  [[ -n "$EP_IDS" ]] && $aws ec2 delete-vpc-endpoints --vpc-endpoint-ids "$EP_IDS" 2>/dev/null || true

  INSTANCE_IDS=$($aws ec2 describe-instances \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=instance-state-name,Values=running,stopped" \
    --query "Reservations[*].Instances[*].InstanceId" --output text 2>/dev/null | tr '\t' ' ')
  if [[ -n "$INSTANCE_IDS" ]]; then
    $aws ec2 terminate-instances --instance-ids "$INSTANCE_IDS" 2>/dev/null || true
    $aws ec2 wait instance-terminated --instance-ids "$INSTANCE_IDS" 2>/dev/null || true
  fi

  for sg in $($aws ec2 describe-security-groups \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query "SecurityGroups[?GroupName!='default'].GroupId" \
    --output text 2>/dev/null | tr '\t' ' '); do
    $aws ec2 delete-security-group --group-id "$sg" 2>/dev/null || true
  done

  for sn in $($aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query "Subnets[*].SubnetId" --output text 2>/dev/null | tr '\t' ' '); do
    $aws ec2 delete-subnet --subnet-id "$sn" 2>/dev/null || true
  done

  for rt in $($aws ec2 describe-route-tables \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query "RouteTables[?!Associations[?Main==\`true\`]].RouteTableId" \
    --output text 2>/dev/null | tr '\t' ' '); do
    $aws ec2 delete-route-table --route-table-id "$rt" 2>/dev/null || true
  done

  for igw in $($aws ec2 describe-internet-gateways \
    --filters "Name=attachment.vpc-id,Values=$VPC_ID" \
    --query "InternetGateways[*].InternetGatewayId" --output text 2>/dev/null | tr '\t' ' '); do
    $aws ec2 detach-internet-gateway \
      --internet-gateway-id "$igw" --vpc-id "$VPC_ID" 2>/dev/null || true
    $aws ec2 delete-internet-gateway --internet-gateway-id "$igw" 2>/dev/null || true
  done

  $aws ec2 delete-vpc --vpc-id "$VPC_ID" 2>/dev/null || true
  echo "  Deleted VPC $VPC_ID"
done

##### S3 #####
echo ""
echo "==> S3"
for bucket in $(aws s3api list-buckets \
  --query "Buckets[?starts_with(Name,'${P}-files-') || starts_with(Name,'${P}-logging-')].Name" \
  --output text 2>/dev/null | tr '\t' ' '); do
  echo "  Emptying and deleting s3://$bucket"
  aws s3 rm "s3://$bucket" --recursive 2>/dev/null || true
  aws s3api delete-bucket --bucket "$bucket" 2>/dev/null || true
done

##### DYNAMODB #####
echo ""
echo "==> DynamoDB"
$aws dynamodb delete-table --table-name "documents-metadata" 2>/dev/null || true
$aws dynamodb delete-table --table-name "userdata" 2>/dev/null || true

###### SECRETS MANAGER #####
echo ""
echo "==> Secrets Manager"
$aws secretsmanager delete-secret \
  --secret-id "${P}-app-secrets" \
  --force-delete-without-recovery 2>/dev/null || true

##### SSM PARAMETERS #####
echo ""
echo "==> SSM Parameters"
for param in $($aws ssm get-parameters-by-path \
  --path "/${P}" --recursive \
  --query "Parameters[*].Name" --output text 2>/dev/null | tr '\t' ' '); do
  $aws ssm delete-parameter --name "$param" 2>/dev/null || true
done

# ##### IAM #####
echo ""
echo "==> IAM"
for role in "api-gateway-logs-role" \
            "${P}-lambda-role" \
            "${P}-secrets-access-role" \
            "${P}-nat-instance-role" \
            "${P}-ecs-execution-role" \
            "${P}-ecs-task-role"; do
  for arn in $($aws iam list-attached-role-policies --role-name "$role" \
    --query "AttachedPolicies[*].PolicyArn" --output text 2>/dev/null | tr '\t' ' '); do
    $aws iam detach-role-policy --role-name "$role" --policy-arn "$arn" 2>/dev/null || true
  done
  for pol in $($aws iam list-role-policies --role-name "$role" \
    --query "PolicyNames" --output text 2>/dev/null | tr '\t' ' '); do
    $aws iam delete-role-policy --role-name "$role" --policy-name "$pol" 2>/dev/null || true
  done
  $aws iam delete-role --role-name "$role" 2>/dev/null || true
done
$aws iam remove-role-from-instance-profile \
  --instance-profile-name "${P}-nat-instance-profile" \
  --role-name "${P}-nat-instance-role" 2>/dev/null || true
$aws iam delete-instance-profile \
  --instance-profile-name "${P}-nat-instance-profile" 2>/dev/null || true

###### CLOUDWATCH LOG GROUPS #####
echo ""
echo "==> CloudWatch Log Groups"
for prefix in "/ecs/${P}" "/aws/apigateway"; do
  for group in $($aws logs describe-log-groups \
    --log-group-name-prefix "$prefix" \
    --query "logGroups[*].logGroupName" --output text 2>/dev/null | tr '\t' ' '); do
    $aws logs delete-log-group --log-group-name "$group" 2>/dev/null || true
  done
done

echo ""
echo "========================================"
echo " Cleanup complete — ACM and Route53 preserved"
echo "========================================"
