#!/usr/bin/python3

from datetime import datetime
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from v1.routes.upload import invalidate_cloudfront_path


def test_invalidate_cloudfront_path_success(client):
    """Test successful invalidation of a CloudFront path"""
    distribution_id = "test-distribution-id"

    mock_response = {
        'Invalidation': {
            'Id': 'I1234567890EXAMPLE',
            'Status': 'InProgress',
            'CreateTime': datetime.now(),
            'InvalidationBatch': {
                'Paths': {
                    'Quantity': 1,
                    'Items': ['/documents/testfile.txt']
                },
                'CallerReference': 'test-ref'
            }
        }
    }

    with patch("v1.routes.upload.boto3.client") as mock_boto3:
        mock_client = MagicMock()
        mock_client.create_invalidation.return_value = mock_response
        mock_boto3.return_value = mock_client

        with patch("v1.routes.upload.Config") as mock_config:
            mock_config.CLOUDFRONT_DISTRIBUTION_ID = distribution_id

            file_key = "documents/testfile.txt"
            result = invalidate_cloudfront_path(file_key)

            mock_client.create_invalidation.assert_called_once()
            assert result is True


def test_invalidate_cloudfront_path_empty_file_key(client):
    """Test invalidation with an empty file_key"""
    with patch("v1.routes.upload.Config") as mock_config:
        mock_config.CLOUDFRONT_DISTRIBUTION_ID = "test-distribution-id"

        file_key = ""
        result = invalidate_cloudfront_path(file_key)
        assert result is False


def test_invalidate_cloudfront_path_client_error(client):
    """Test invalidation when CloudFront client raises an error"""
    with patch("v1.routes.upload.Config") as mock_config:
        mock_config.CLOUDFRONT_DISTRIBUTION_ID = "test-distribution-id"

        with patch("boto3.client") as mock_boto3:
            mock_boto3.return_value.create_invalidation.side_effect = (
                    ClientError(
                        {
                            "Error":
                            {
                                "Code": "InvalidArgument",
                                "Message": "Invalid distribution ID"
                            }
                        },
                        "CreateInvalidation",
                    )
                )
            file_key = "documents/testfile.txt"
            result = invalidate_cloudfront_path(file_key)
            assert result is False


def test_invalidate_cloudfront_path_unexpected_error(client):
    """Test invalidation when an unexpected error occurs"""
    with patch("v1.routes.upload.Config") as mock_config:
        mock_config.CLOUDFRONT_DISTRIBUTION_ID = "test-distribution-id"

        with patch("boto3.client") as mock_boto3:
            error = Exception("Unexpected error")
            mock_boto3.return_value.create_invalidation.side_effect = error

            file_key = "documents/testfile.txt"
            result = invalidate_cloudfront_path(file_key)
            assert result is False
