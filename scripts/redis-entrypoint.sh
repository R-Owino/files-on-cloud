#!/bin/sh
set -e

# Get Redis password from AWS Secrets Manager
REDIS_PASSWORD=$(aws secretsmanager get-secret-value \
    --secret-id "${AWS_SECRET_NAME:-filesoncloud-app-secrets}" \
    --region "${AWS_REGION:-us-west-2}" \
    --query SecretString \
    --output text | jq -r '.REDIS_PASSWORD')

if [ "$REDIS_PASSWORD" = "null" ] || [ -z "$REDIS_PASSWORD" ]; then
    echo "Warning: No Redis password found, starting without auth"
    exec redis-server --bind 0.0.0.0
else
    echo "Starting Redis with authentication"
    exec redis-server --bind 0.0.0.0 --requirepass "$REDIS_PASSWORD"
fi
