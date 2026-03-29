import os
import sys
import time
import logging
import psutil
import redis
import boto3
from flask import Blueprint, jsonify, current_app
from botocore.exceptions import ClientError, NoCredentialsError
from v1.config import Config


logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


def check_redis_connection():
    """Check Redis connectivity using the same connection as Flask-Session."""
    try:
        if 'pytest' in sys.modules:
            return True, "Redis check skipped in test environment"

        # first use the same Redis connection as Flask-Session
        try:
            session_redis = current_app.config.get("SESSION_REDIS")
            if session_redis:
                session_redis.ping()

                # Test basic operations
                test_key = "health_check_test"
                session_redis.set(test_key, "test_value", ex=10)
                value = session_redis.get(test_key)
                session_redis.delete(test_key)

                if value == b"test_value" or value == "test_value":
                    return True, (
                        "Redis connection successful (using Flask session)"
                    )
                return False, "Redis read/write test failed"
        except Exception as e:
            logger.debug(f"Flask session Redis failed: {e}")

        # Fallback to manual Redis connection
        redis_url = Config.get_redis_url()
        redis_client = redis.from_url(redis_url)

        # Test connection
        redis_client.ping()

        # Test basic operations
        test_key = "health_check_test"
        redis_client.set(test_key, "test_value", ex=10)
        value = redis_client.get(test_key)
        redis_client.delete(test_key)

        if value == b"test_value" or value == "test_value":
            host_part = (
                redis_url.split('@')[1].split(':')[0]
                if '@' in redis_url
                else redis_url.split('://')[1].split(':')[0]
            )
            return True, (
                f"Redis connection successful"
                f"(manual connection to {host_part})"
            )
        return False, "Redis read/write test failed"

    except redis.ConnectionError as e:
        return False, f"Redis connection failed: {str(e)}"
    except Exception as e:
        return False, f"Redis check failed: {str(e)}"


def check_aws_services():
    """
    Check connectivity with configured AWS services.

    Returns:
        dict: A dictionary with status information for each AWS service.
    """
    aws_checks = {}
    region = Config.AWS_REGION

    def _check_service(
            service_key,
            config_flag,
            client_name,
            check_func,
            healthy_msg,
            error_prefix):
        """
        Helper function to check an individual AWS service.

        Args:
            service_key: Key to use in the results dictionary
            config_flag: Configuration flag to check if service is enabled
            client_name: Name of the boto3 client to create
            check_func: Function that performs the service check
            healthy_msg: Message to use when service is healthy
            error_prefix: Prefix for error messages
        """
        if not config_flag:
            return

        try:
            client = boto3.client(client_name, region_name=region)
            check_func(client)
            aws_checks[service_key] = {
                'status': 'healthy',
                'message': healthy_msg
            }
        except ClientError as e:
            aws_checks[service_key] = {
                'status': 'unhealthy',
                'message': f'{error_prefix}: {str(e)}'
            }
        except Exception as e:
            aws_checks[service_key] = {
                'status': 'unhealthy',
                'message': f'{error_prefix} check failed: {str(e)}'
            }

    try:
        # Cognito check
        _check_service(
            'cognito',
            Config.AWS_COGNITO_USER_POOL_ID,
            'cognito-idp',
            lambda c: c.describe_user_pool(
                UserPoolId=Config.AWS_COGNITO_USER_POOL_ID
            ),
            'Cognito accessible',
            'Cognito error'
        )

        # S3 check
        _check_service(
            's3',
            Config.S3_BUCKET_NAME,
            's3',
            lambda c: c.head_bucket(Bucket=Config.S3_BUCKET_NAME),
            'S3 bucket accessible',
            'S3 error'
        )

        # DynamoDB Documents Table check
        _check_service(
            'dynamodb_documents',
            Config.DOCUMENTS_DYNAMODB_TABLE_NAME,
            'dynamodb',
            lambda c: c.describe_table(
                TableName=Config.DOCUMENTS_DYNAMODB_TABLE_NAME
            ),
            'Documents table accessible',
            'DynamoDB documents error'
        )

        # DynamoDB Userdata Table check
        _check_service(
            'dynamodb_userdata',
            Config.USERDATA_DYNAMODB_TABLE_NAME,
            'dynamodb',
            lambda c: c.describe_table(
                TableName=Config.USERDATA_DYNAMODB_TABLE_NAME
            ),
            'Userdata table accessible',
            'DynamoDB userdata error'
        )

        # CloudFront check
        _check_service(
            'cloudfront',
            Config.CLOUDFRONT_DISTRIBUTION_ID,
            'cloudfront',
            lambda c: c.get_distribution(
                Id=Config.CLOUDFRONT_DISTRIBUTION_ID
            ),
            'CloudFront distribution accessible',
            'CloudFront error'
        )

    except NoCredentialsError:
        aws_checks['aws_credentials'] = {
            'status': 'unhealthy',
            'message': 'AWS credentials not found'
        }
    except Exception as e:
        aws_checks['aws_general'] = {
            'status': 'unhealthy',
            'message': f'AWS check failed: {str(e)}'
        }

    return aws_checks


def check_system_resources():
    """Check system resource usage."""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent

        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent

        # Process count
        process_count = len(psutil.pids())

        # Load average - for Unix-like systems
        load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else None

        resources = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'disk_percent': disk_percent,
            'process_count': process_count,
            'load_average': load_avg
        }

        # Determine if resources are healthy
        is_healthy = (
            cpu_percent < 80 and
            memory_percent < 85 and
            disk_percent < 90
        )

        return is_healthy, resources

    except Exception as e:
        return False, f"System resource check failed: {str(e)}"


def check_application_health():
    """Check application-specific health."""
    try:
        # Check if Flask app is running
        app_status = current_app is not None

        # Check critical environment variables
        critical_vars = [
            'SECRET_KEY',
            'AWS_REGION',
            'AWS_COGNITO_USER_POOL_ID',
            'AWS_COGNITO_CLIENT_ID'
        ]

        missing_vars = [
            var for var in critical_vars
            if not getattr(Config, var, None)
        ]

        app_info = {
            'flask_app_running': app_status,
            'missing_critical_vars': missing_vars,
            'python_version': sys.version,
            'environment': 'test' if 'pytest' in sys.modules else 'production'
        }

        is_healthy = app_status and not missing_vars

        return is_healthy, app_info

    except Exception as e:
        return False, f"Application health check failed: {str(e)}"


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check endpoint"""
    start_time = time.time()

    health_status = {
        'timestamp': time.time(),
        'status': 'healthy',
        'checks': {}
    }

    overall_healthy = True

    # Check Redis
    redis_healthy, redis_message = check_redis_connection()
    health_status['checks']['redis'] = {
        'status': 'healthy' if redis_healthy else 'unhealthy',
        'message': redis_message
    }
    if not redis_healthy:
        overall_healthy = False

    # Check AWS services
    aws_checks = check_aws_services()
    health_status['checks']['aws'] = aws_checks

    # Check if any AWS service is unhealthy
    if any(
        check.get('status') == 'unhealthy'
        for check in aws_checks.values()
    ):
        overall_healthy = False

    # Check system resources
    resources_healthy, resources_info = check_system_resources()
    health_status['checks']['system_resources'] = {
        'status': 'healthy' if resources_healthy else 'unhealthy',
        'details': resources_info
    }
    if not resources_healthy:
        overall_healthy = False

    # Check application health
    app_healthy, app_info = check_application_health()
    health_status['checks']['application'] = {
        'status': 'healthy' if app_healthy else 'unhealthy',
        'details': app_info
    }
    if not app_healthy:
        overall_healthy = False

    # Overall status
    health_status['status'] = 'healthy' if overall_healthy else 'unhealthy'
    health_status['response_time_ms'] = round(
        (time.time() - start_time) * 1000, 2
    )

    # Return appropriate HTTP status code
    status_code = 200 if overall_healthy else 503

    return jsonify(health_status), status_code


@health_bp.route('/health/liveness', methods=['GET'])
def liveness_check():
    """
    Liveness check - basic app functionality

    Returns:
        Response: JSON response with status and timestamp
    """
    try:
        # basic check that the app is running
        app_running = current_app is not None

        response_data = {
            'status': 'alive' if app_running else 'dead',
            'timestamp': time.time()
        }
        status_code = 200 if app_running else 503

        return jsonify(response_data), status_code

    except Exception as e:
        return jsonify({
            'status': 'dead',
            'error': str(e),
            'timestamp': time.time()
        }), 503


@health_bp.route('/health/readiness', methods=['GET'])
def readiness_check():
    """
    Readiness check - application is ready to serve traffic

    Returns:
        Response: JSON response with status and dependency checks
    """
    try:
        # check critical dependencies
        redis_healthy, _ = check_redis_connection()

        # check at least one AWS service
        cognito_healthy = True
        if Config.AWS_COGNITO_USER_POOL_ID:
            try:
                cognito_client = boto3.client(
                    'cognito-idp',
                    region_name=Config.AWS_REGION
                )
                cognito_client.describe_user_pool(
                    UserPoolId=Config.AWS_COGNITO_USER_POOL_ID
                )
            except Exception:
                cognito_healthy = False

        # app is ready if Redis and Cognito are healthy
        is_ready = redis_healthy and cognito_healthy

        response_data = {
            'status': 'ready' if is_ready else 'not_ready',
            'redis': redis_healthy,
            'cognito': cognito_healthy,
            'timestamp': time.time()
        }
        status_code = 200 if is_ready else 503

        return jsonify(response_data), status_code

    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': time.time()
        }), 503
