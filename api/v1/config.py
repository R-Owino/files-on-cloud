import boto3
import json
import os
import logging
from typing import Optional, Dict
from botocore.exceptions import (
    ClientError,
    NoCredentialsError,
    PartialCredentialsError
)

logger = logging.getLogger(__name__)


class Config:
    """App configurations with AWS Secrets Manager and
    Parameter Store support"""

    _secrets_cache = None
    _parameters_cache = None

    @classmethod
    def _get_aws_secrets(cls):
        """Retrieve secrets from AWS Secrets Manager"""
        if cls._secrets_cache is not None:
            return cls._secrets_cache

        secret_name = os.getenv("AWS_SECRET_NAME", "filesoncloud-app-secrets")
        region_name = os.getenv("AWS_REGION", "us-west-2")

        try:
            session = boto3.session.Session()  # type: ignore[attr-defined]
            client = session.client(
                service_name='secretsmanager',
                region_name=region_name
            )

            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name
            )
            secret = get_secret_value_response['SecretString']
            cls._secrets_cache = json.loads(secret)
            logger.info("Successfully loaded secrets from AWS Secrets Manager")
            return cls._secrets_cache

        except ClientError as e:
            logger.error(f"Could not retrieve secrets from AWS: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading secrets: {e}")
            raise

    @classmethod
    def _get_parameter_store_values(cls) -> Dict[str, str]:
        """Retrieve configuration from AWS Parameter Store"""
        if cls._parameters_cache is not None:
            return cls._parameters_cache

        project_name = os.getenv("PROJECT_NAME", "filesoncloud")
        region_name = os.getenv("AWS_REGION", "us-west-2")
        base_path = f"/{project_name}"

        try:
            session = boto3.session.Session()  # type: ignore[attr-defined]
            client = session.client(
                service_name='ssm',
                region_name=region_name
            )

            # Get all parameters under the base path
            paginator = client.get_paginator('get_parameters_by_path')
            parameters = {}

            for page in paginator.paginate(
                Path=base_path,
                Recursive=True,
                WithDecryption=False
            ):
                for param in page['Parameters']:
                    # Extract just the parameter name without the path
                    param_name = param['Name'].split('/')[-1]
                    parameters[param_name] = param['Value']

            cls._parameters_cache = parameters
            logger.info(
                f"Successfully loaded {len(parameters)} parameters "
                f"from Parameter Store"
            )
            return cls._parameters_cache

        except ClientError as e:
            logger.warning(f"Could not retrieve parameters from AWS: {e}")
            return {}
        except Exception as e:
            logger.warning(f"Error loading parameters: {e}")
            return {}

    @classmethod
    def _get_config_value(cls, key, default=None):
        """Get config value from environment, Secrets Manager, or
        Parameter Store"""
        # First, check environment variables (highest priority for ECS secrets)
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value

        # Second, check AWS Secrets Manager for sensitive values
        try:
            secrets = cls._get_aws_secrets()
            if key in secrets:
                return secrets[key]
        except (
            ClientError,
            NoCredentialsError,
            PartialCredentialsError,
            json.JSONDecodeError
        ) as e:
            logger.warning(f"Could not load secrets for {key}: {e}")

        # Third, check Parameter Store for configuration values
        try:
            parameters = cls._get_parameter_store_values()
            if key in parameters:
                return parameters[key]
        except Exception as e:
            logger.warning(f"Could not load parameter {key}: {e}")

        # Finally, return default
        return default

    # Configuration values
    SECRET_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = None
    AWS_COGNITO_USER_POOL_ID: Optional[str] = None
    AWS_COGNITO_CLIENT_ID: Optional[str] = None
    AWS_API_GATEWAY_FETCH_METADATA_URL: Optional[str] = None
    AWS_API_GATEWAY_DELETE_URL: Optional[str] = None
    S3_BUCKET_NAME: Optional[str] = None
    DOCUMENTS_DYNAMODB_TABLE_NAME: Optional[str] = None
    USERDATA_DYNAMODB_TABLE_NAME: Optional[str] = None
    CLOUDFRONT_DOMAIN: Optional[str] = None
    CLOUDFRONT_PUBLIC_KEY_ID: Optional[str] = None
    CLOUDFRONT_DISTRIBUTION_ID: Optional[str] = None
    REDIS_HOST: Optional[str] = None
    REDIS_ECS: Optional[str] = None
    REDIS_PORT: Optional[int] = None
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: Optional[str] = None

    @classmethod
    def get_redis_url(cls):
        """Generate Redis URL from components with environment awareness"""
        # Return direct URL if provided
        if cls.REDIS_URL:
            return cls.REDIS_URL

        # Environment-specific host selection
        environment = os.getenv("ENVIRONMENT", "local")

        if environment == "prod":
            # Production: Redis runs in same ECS task as localhost
            redis_host = "localhost"
            redis_port = cls.REDIS_PORT or 6379
            redis_password = cls.REDIS_PASSWORD
        else:
            # Local development: Redis runs as separate container
            redis_host = os.getenv("REDIS_HOST", "redis")
            redis_port = cls.REDIS_PORT or 6379
            redis_password = cls.REDIS_PASSWORD

        if redis_password:
            return f"redis://:{redis_password}@{redis_host}:{redis_port}"
        else:
            return f"redis://{redis_host}:{redis_port}"

    @classmethod
    def initialize(cls):
        """Initialize all configuration values"""
        cls.SECRET_KEY = cls._get_config_value(
            "SECRET_KEY", "xyz-xyz-xyz"
        )
        cls.AWS_REGION = cls._get_config_value(
            "AWS_REGION", "us-west-2"
        )
        cls.AWS_COGNITO_USER_POOL_ID = cls._get_config_value(
            "AWS_COGNITO_USER_POOL_ID"
        )
        cls.AWS_COGNITO_CLIENT_ID = cls._get_config_value(
            "AWS_COGNITO_CLIENT_ID"
        )
        cls.AWS_API_GATEWAY_FETCH_METADATA_URL = cls._get_config_value(
            "AWS_API_GATEWAY_FETCH_METADATA_URL"
        )
        cls.AWS_API_GATEWAY_DELETE_URL = cls._get_config_value(
            "AWS_API_GATEWAY_DELETE_URL"
        )
        cls.S3_BUCKET_NAME = cls._get_config_value(
            "S3_BUCKET_NAME"
        )
        cls.DOCUMENTS_DYNAMODB_TABLE_NAME = cls._get_config_value(
            "DOCUMENTS_DYNAMODB_TABLE_NAME"
        )
        cls.USERDATA_DYNAMODB_TABLE_NAME = cls._get_config_value(
            "USERDATA_DYNAMODB_TABLE_NAME"
        )
        cls.CLOUDFRONT_DOMAIN = cls._get_config_value(
            "CLOUDFRONT_DOMAIN"
        )
        cls.CLOUDFRONT_PUBLIC_KEY_ID = cls._get_config_value(
            "CLOUDFRONT_PUBLIC_KEY_ID"
        )
        cls.CLOUDFRONT_DISTRIBUTION_ID = cls._get_config_value(
            "CLOUDFRONT_DISTRIBUTION_ID"
        )
        cls.REDIS_HOST = cls._get_config_value(
            "REDIS_HOST", "redis"
        )
        cls.REDIS_ECS = cls._get_config_value(
            "REDIS_ECS", "localhost"
        )
        cls.REDIS_PASSWORD = cls._get_config_value(
            "REDIS_PASSWORD"
        )
        cls.REDIS_PORT = int(cls._get_config_value("REDIS_PORT", "6379"))
        cls.REDIS_URL = cls._get_config_value("REDIS_URL")

        redis_url = cls.get_redis_url()
        if '@' in redis_url:
            host_part = redis_url.split('@')[-1]
        else:
            host_part = redis_url.replace('redis://', '')
        logger.info(
            f"Redis will connect to: redis://[credentials]@{host_part}"
        )


# Initialize configuration values
Config.initialize()
