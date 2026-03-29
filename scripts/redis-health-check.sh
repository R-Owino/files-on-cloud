#!/bin/sh

# Get Redis password from AWS Secrets Manager for health check
SECRET_NAME="${AWS_SECRET_NAME:-filesoncloud-app-secrets}"
REGION="${AWS_REGION:-us-west-2}"

REDIS_PASSWORD=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_NAME" \
    --region "$REGION" \
    --query SecretString \
    --output text | jq -r '.REDIS_PASSWORD' 2>/dev/null)

if [ "$REDIS_PASSWORD" != "null" ] && [ -n "$REDIS_PASSWORD" ]; then
    redis-cli -a "$REDIS_PASSWORD" ping
else
    redis-cli ping
fi
