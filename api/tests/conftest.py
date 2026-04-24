import pytest
import os
import sys
from unittest.mock import patch
from cachelib import SimpleCache

sys.path.insert(0,
                os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import v1.config


@pytest.fixture(autouse=True)
def mock_redis():
    """Mock Redis connection for tests"""
    with patch('redis.from_url') as mock_redis:
        yield mock_redis


@pytest.fixture(autouse=True)
def mock_aws_config():
    """Patch Config class attributes and module-level route variables that
    would be None without live AWS infrastructure.

    Routes copy Config values into module-level variables at import time,
    so we patch both the Config class and those copies.
    """
    with patch.object(v1.config.Config, 'S3_BUCKET_NAME', 'test-bucket'), \
         patch.object(v1.config.Config, 'AWS_REGION', 'us-west-2'), \
         patch.object(v1.config.Config, 'CLOUDFRONT_DOMAIN',
                      'test.cloudfront.net'), \
         patch.object(v1.config.Config, 'CLOUDFRONT_PUBLIC_KEY_ID',
                      'TEST_KEY_ID'), \
         patch('v1.routes.download.BUCKET_NAME', 'test-bucket'), \
         patch('v1.routes.download.CLOUDFRONT_DOMAIN',
               'test.cloudfront.net'), \
         patch('v1.routes.download.KEY_PAIR_ID', 'TEST_KEY_ID'), \
         patch('v1.routes.file_metadata.AWS_API_GATEWAY_FETCH_METADATA_URL',
               'https://test-api.example.com'), \
         patch('v1.routes.search_file.AWS_API_GATEWAY_FETCH_METADATA_URL',
               'https://test-api.example.com'):
        yield


@pytest.fixture
def client():
    from v1.app import app

    # Update session configuration to use cachelib
    app.config.update({
        "TESTING": True,
        "SESSION_TYPE": "cachelib",
        "SESSION_CACHELIB": SimpleCache(),
    })

    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def clear_session_cache(request):
    """Clear session cache between tests for Flask client tests"""
    # Only proceed if the test uses the Flask client fixture
    if 'client' in request.fixturenames:
        client = request.getfixturevalue('client')
        cache = client.application.config['SESSION_CACHELIB']
        cache.clear()
