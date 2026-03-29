import pytest
import boto3
import requests
import json
from v1.app import app
from v1.config import Config
from moto import mock_aws
from unittest.mock import patch, MagicMock, ANY
from flask.testing import FlaskClient
from botocore.exceptions import ClientError


@pytest.fixture
def client():
    """Create a test client for the Flask application"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_s3():
    """Mock S3 client and bucket setup"""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-west-2")
        s3.create_bucket(
            Bucket=Config.S3_BUCKET_NAME,
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"}
        )
        yield s3


def test_download_file_unauthorized(client: FlaskClient):
    """Test GET /download fails if user is not logged in"""
    response = client.get("/download?file_key=testfile.txt")
    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"


def test_download_file_missing_file_key(client: FlaskClient):
    """Test GET /download fails if file_key parameter is missing"""
    with client.session_transaction() as session:
        session["email"] = "testuser@example.com"

    response = client.get("/download")
    assert response.status_code == 400
    assert response.get_json()["error"] == (
        "Missing required parameter: file_key"
    )


def test_download_file_success_with_cloudfront(client: FlaskClient, mock_s3):
    """
    Test successful generation of cloudfront signed URL with custom policy
    """
    with client.session_transaction() as session:
        session["email"] = "testuser@example.com"

    mock_s3.put_object(
        Bucket=Config.S3_BUCKET_NAME,
        Key="documents/testfile.txt",
        Body=b"test content"
    )

    with patch("v1.routes.download.s3.head_object") as mock_head_object:
        with patch("v1.routes.download.wait") as mock_wait:
            mock_wait.return_value = True
            with patch(
                "v1.routes.download.cloudfront_signer.generate_presigned_url"
            ) as mock_generate_url:
                mock_generate_url.return_value = (
                    "https://cloudfront.example.com/signed-url"
                )

                response = client.get(
                    "/download?file_key=documents/testfile.txt"
                )
                assert response.status_code == 200
                data = response.get_json()
                assert "presigned_url" in data
                assert data["presigned_url"] == (
                    "https://cloudfront.example.com/signed-url"
                )
                assert data["file_name"] == "testfile.txt"

                # Verify the custom policy was used
                expected_url = (
                    f"https://{Config.CLOUDFRONT_DOMAIN}"
                    "/documents/testfile.txt"
                )
                mock_generate_url.assert_called_with(
                    expected_url,
                    policy=ANY  # JSON string policy
                )


def test_download_file_fallback_to_s3_presigned_url(
        client: FlaskClient,
        mock_s3):
    """Test fallback to S3 pre-signed URL if cloudfront signing fails"""
    with client.session_transaction() as session:
        session["email"] = "testuser@example.com"

    mock_s3.put_object(
        Bucket=Config.S3_BUCKET_NAME,
        Key="documents/testfile.txt",
        Body=b"test content"
    )

    with patch("v1.routes.download.s3.head_object") as mock_head_object:
        with patch("v1.routes.download.wait") as mock_wait:
            mock_wait.return_value = True
            with patch(
                "v1.routes.download.cloudfront_signer.generate_presigned_url"
            ) as mock_cf_url:
                mock_cf_url.side_effect = Exception(
                    "CloudFront signing failed"
                )
                with patch(
                    "v1.routes.download.s3.generate_presigned_url"
                ) as mock_s3_url:
                    mock_s3_url.return_value = (
                        "https://s3.amazonaws.com/bucket/signed-url"
                    )

                    response = client.get(
                        "/download?file_key=documents/testfile.txt"
                    )
                    assert response.status_code == 200
                    data = response.get_json()
                    assert "presigned_url" in data
                    assert data["presigned_url"] == (
                        "https://s3.amazonaws.com/bucket/signed-url"
                    )


def test_download_file_not_found(client: FlaskClient, mock_s3):
    """Test GET /download returns 404 if file does not exist"""
    with client.session_transaction() as session:
        session["email"] = "testuser@example.com"

    with patch("v1.routes.download.s3.head_object") as mock_head_object:
        mock_head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "HeadObject"
        )

        response = client.get(
            "/download?file_key=documents/missingfile.txt"
        )
        assert response.status_code == 404
        assert response.get_json()["error"] == "File not found"


def test_download_file_access_denied(client: FlaskClient, mock_s3):
    """Test GET /download returns 403 if access to the file is denied"""
    with client.session_transaction() as session:
        session["email"] = "testuser@example.com"

    with patch("v1.routes.download.s3.head_object") as mock_head_object:
        mock_head_object.side_effect = ClientError(
            {"Error": {"Code": "403", "Message": "Access Denied"}},
            "HeadObject"
        )

        response = client.get(
            "/download?file_key=documents/testfile.txt"
        )
        assert response.status_code == 403
        assert response.get_json()["error"] == "Access denied"


def test_download_file_wait_for_file_availability(
        client: FlaskClient,
        mock_s3):
    """Test the wait function for file availability in S3"""
    with client.session_transaction() as session:
        session["email"] = "testuser@example.com"

    mock_s3.put_object(
        Bucket=Config.S3_BUCKET_NAME,
        Key="documents/testfile.txt",
        Body=b"test content"
    )

    with patch("v1.routes.download.s3.head_object") as mock_head_object:
        with patch("v1.routes.download.wait") as mock_wait:
            mock_wait.return_value = False

            response = client.get(
                "/download?file_key=documents/testfile.txt"
            )
            assert response.status_code == 404
            assert response.get_json()["error"] == (
                "File not found or not yet available"
            )
            mock_wait.assert_called_once()


def test_download_file_unexpected_error(client: FlaskClient):
    """Test GET /download handles unexpected errors gracefully"""
    with client.session_transaction() as session:
        session["email"] = "testuser@example.com"

    with patch("v1.routes.download.s3.head_object") as mock_head_object:
        mock_head_object.side_effect = Exception("Unexpected error")

        response = client.get(
            "/download?file_key=documents/testfile.txt"
        )
        assert response.status_code == 500
        assert response.get_json()["error"] == "An unexpected error occured"


def test_download_file_special_characters(client: FlaskClient, mock_s3):
    """
    Test handling of file keys with special characters that need URL encoding
    """
    with client.session_transaction() as session:
        session["email"] = "testuser@example.com"

    special_key = "documents/test file with spaces & special$ chars.txt"
    encoded_key = (
        "documents/test%20file%20with%20spaces%20%26%20special%24%20chars.txt"
    )

    mock_s3.put_object(
        Bucket=Config.S3_BUCKET_NAME,
        Key=special_key,
        Body=b"test content"
    )

    with patch("v1.routes.download.s3.head_object") as mock_head:
        with patch("v1.routes.download.wait") as mock_wait:
            mock_wait.return_value = True
            with patch(
                "v1.routes.download.cloudfront_signer.generate_presigned_url"
            ) as mock_url:
                mock_url.return_value = (
                    "https://cloudfront.example.com/signed-url"
                )

                response = client.get(
                    f"/download?file_key={encoded_key}"
                )
                assert response.status_code == 200
                assert response.get_json()["file_name"] == (
                    "test file with spaces & special$ chars.txt"
                )


def test_download_file_large_timeout(client: FlaskClient, mock_s3):
    """Test handling of timeout during S3 operations"""
    with client.session_transaction() as session:
        session["email"] = "testuser@example.com"

    with patch("v1.routes.download.s3.head_object") as mock_head:
        mock_head.side_effect = ClientError(
            {
                "Error":
                {
                    "Code": "RequestTimeout",
                    "Message": "Request timed out"
                }
            },
            "HeadObject"
        )

        response = client.get(
            "/download?file_key=documents/testfile.txt"
        )
        assert response.status_code == 500
        assert "error" in response.get_json()


def test_proxy_download_endpoint_unauthorized(client: FlaskClient):
    """Test proxy download endpoint fails if user is not logged in"""
    response = client.get("/download/documents/testfile.txt")
    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"


def test_proxy_download_endpoint_success(client: FlaskClient, mock_s3):
    """Test successful proxy download"""
    with client.session_transaction() as session:
        session["email"] = "testuser@example.com"

    mock_s3.put_object(
        Bucket=Config.S3_BUCKET_NAME,
        Key="documents/testfile.txt",
        Body=b"test content"
    )

    with patch("v1.routes.download.s3.head_object") as mock_head:
        with patch("v1.routes.download.wait") as mock_wait:
            mock_wait.return_value = True
            with patch(
                "v1.routes.download.cloudfront_signer.generate_presigned_url"
            ) as mock_url:
                mock_url.return_value = (
                    "https://cloudfront.example.com/signed-url"
                )
                with patch("v1.routes.download.requests.get") as mock_request:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.headers = {
                        "Content-Type": "text/plain",
                        "Content-Length": "12"
                    }
                    mock_response.iter_content.return_value = [b"test content"]
                    mock_request.return_value = mock_response

                    response = client.get(
                        "/download/documents/testfile.txt"
                    )
                    assert response.status_code == 200
                    assert response.headers["Content-Disposition"] == (
                        'attachment; filename="testfile.txt"'
                    )


def test_proxy_download_endpoint_remote_failure(client: FlaskClient, mock_s3):
    """Test proxy download when remote fetch fails"""
    with client.session_transaction() as session:
        session["email"] = "testuser@example.com"

    with patch("v1.routes.download.generate_download_url") as mock_generate:
        mock_generate.return_value = (
            "https://cloudfront.example.com/signed-url",
            "testfile.txt",
            None,
            200
        )
        with patch("v1.routes.download.requests.get") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_request.return_value = mock_response

            response = client.get(
                "/download/documents/testfile.txt"
            )
            assert response.status_code == 403


def test_proxy_download_endpoint_connection_error(client: FlaskClient):
    """Test proxy download when connection to remote server fails"""
    with client.session_transaction() as session:
        session["email"] = "testuser@example.com"

    with patch("v1.routes.download.generate_download_url") as mock_generate:
        mock_generate.return_value = (
            "https://cloudfront.example.com/signed-url",
            "testfile.txt",
            None,
            200
        )
        with patch("v1.routes.download.requests.get") as mock_request:
            mock_request.side_effect = (
                requests.RequestException("Connection failed")
            )

            response = client.get(
                "/download/documents/testfile.txt"
            )
            assert response.status_code == 500
            assert response.get_json()["error"] == "Failed to fetch file"


def test_download_file_both_signing_methods_fail(client: FlaskClient, mock_s3):
    """Test handling when both CloudFront and S3 URL generation fail"""
    with client.session_transaction() as session:
        session["email"] = "testuser@example.com"

    mock_s3.put_object(
        Bucket=Config.S3_BUCKET_NAME,
        Key="documents/testfile.txt",
        Body=b"test content"
    )

    with patch("v1.routes.download.s3.head_object") as mock_head_object:
        with patch("v1.routes.download.wait") as mock_wait:
            mock_wait.return_value = True

            with patch(
                "v1.routes.download.cloudfront_signer.generate_presigned_url"
            ) as mock_cf_url:
                mock_cf_url.side_effect = Exception(
                    "CloudFront signing failed"
                )

                with patch(
                    "v1.routes.download.s3.generate_presigned_url"
                ) as mock_s3_url:
                    mock_s3_url.side_effect = ClientError(
                        {
                            "Error":
                            {
                                "Code": "InternalError",
                                "Message": "S3 internal error"
                            }
                        },
                        "GeneratePresignedUrl"
                    )

                    response = client.get(
                        "/download?file_key=documents/testfile.txt"
                    )
                    assert response.status_code == 500
                    assert response.get_json()["error"] == (
                        "Failed to generate download URL"
                    )


def test_custom_policy_generation(client: FlaskClient, mock_s3):
    """Test that the custom policy is correctly generated and used"""
    with client.session_transaction() as session:
        session["email"] = "testuser@example.com"

    mock_s3.put_object(
        Bucket=Config.S3_BUCKET_NAME,
        Key="documents/testfile.txt",
        Body=b"test content"
    )

    with patch("v1.routes.download.s3.head_object") as mock_head_object:
        with patch("v1.routes.download.wait") as mock_wait:
            mock_wait.return_value = True
            with patch(
                "v1.routes.download.cloudfront_signer.generate_presigned_url"
            ) as mock_generate_url:
                mock_generate_url.return_value = (
                    "https://cloudfront.example.com/signed-url"
                )

                response = client.get(
                    "/download?file_key=documents/testfile.txt"
                )

                # Verify the custom policy was used
                mock_generate_url.assert_called_once()
                args, kwargs = mock_generate_url.call_args

                # Check that policy argument was passed
                assert "policy" in kwargs
                policy = json.loads(kwargs["policy"])

                # Verify policy structure
                assert "Statement" in policy
                assert len(policy["Statement"]) == 1
                statement = policy["Statement"][0]

                # Verify resource matches expected CloudFront URL
                expected_url = (
                    f"https://{Config.CLOUDFRONT_DOMAIN}"
                    "/documents/testfile.txt"
                )
                assert statement["Resource"] == expected_url

                # Verify condition contains DateLessThan
                assert "Condition" in statement
                assert "DateLessThan" in statement["Condition"]
                assert "AWS:EpochTime" in statement["Condition"]["DateLessThan"]  # noqa E501
