#!/usr/bin/python3

import hashlib
import pytest
import requests
import json
from unittest.mock import patch, MagicMock
from v1.app import app


@pytest.fixture
def client():
    """Create a test client for the Flask application"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis_mock = MagicMock()
    with patch(
        'v1.routes.file_metadata.get_redis_client',
        return_value=redis_mock
    ):
        yield redis_mock


def test_file_metadata_missing_config(client):
    """Test metadata retrieval fails when config is missing"""
    with patch(
        'v1.routes.file_metadata.AWS_API_GATEWAY_FETCH_METADATA_URL', ''
    ):
        response = client.get("/file-metadata")
        assert response.status_code == 500
        assert response.get_json()["error"] == (
            "Server misconfiguration: missing API URL."
        )


@patch("requests.get")
def test_file_metadata_no_cache(mock_get, client, mock_redis):
    """Test successful metadata retrieval with cache miss"""
    mock_redis.get.return_value = None

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "files": ["file1.txt", "file2.pdf"]
    }

    response = client.get("/file-metadata")

    assert response.status_code == 200
    assert response.get_json() == {"files": ["file1.txt", "file2.pdf"]}

    mock_redis.get.assert_called_once_with("file_metadata:public")
    mock_redis.setex.assert_called_once()


@patch("requests.get")
def test_file_metadata_cache_hit(mock_get, client, mock_redis):
    """Test successful metadata retrieval with cache hit"""
    cached_data = {"files": ["cached_file1.txt", "cached_file2.pdf"]}
    mock_redis.get.return_value = json.dumps(cached_data)

    response = client.get("/file-metadata")

    assert response.status_code == 200
    assert response.get_json() == cached_data

    mock_get.assert_not_called()
    mock_redis.get.assert_called_once_with("file_metadata:public")


@patch("requests.get")
def test_file_metadata_authenticated_user(mock_get, client, mock_redis):
    """Test metadata retrieval with authenticated user"""
    mock_redis.get.return_value = None

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"files": ["auth_file.txt"]}

    auth_header = "Bearer test.jwt.token"
    response = client.get(
        "/file-metadata",
        headers={"Authorization": auth_header}
    )

    assert response.status_code == 200

    auth_hash = hashlib.md5(auth_header.encode()).hexdigest()[:8]
    expected_cache_key = f"file_metadata:auth{auth_hash}"
    mock_redis.get.assert_called_with(expected_cache_key)

    mock_get.assert_called_once()
    call_args = mock_get.call_args
    assert call_args[1]["headers"]["Authorization"] == auth_header


@patch("requests.get")
def test_file_metadata_cache_read_error(mock_get, client, mock_redis):
    """Test handling of cache read errors"""
    mock_redis.get.side_effect = Exception("Redis connection failed")

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"files": ["file1.txt"]}

    response = client.get("/file-metadata")

    assert response.status_code == 200
    assert response.get_json() == {"files": ["file1.txt"]}

    mock_get.assert_called_once()


@patch("requests.get")
def test_file_metadata_cache_write_error(mock_get, client, mock_redis):
    """Test handling of cache write errors"""
    mock_redis.get.return_value = None

    mock_redis.setex.side_effect = Exception("Redis write failed")

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"files": ["file1.txt"]}

    response = client.get("/file-metadata")

    assert response.status_code == 200
    assert response.get_json() == {"files": ["file1.txt"]}


@patch("requests.get")
def test_file_metadata_api_failure(mock_get, client, mock_redis):
    """Test metadata retrieval failure due to API failure"""
    mock_redis.get.return_value = None
    mock_get.return_value.status_code = 500
    mock_get.return_value.text = "Internal Server Error"

    response = client.get("/file-metadata")
    assert response.status_code == 500
    assert response.get_json()["error"] == (
        "Failed to fetch files: Internal Server Error"
    )

    mock_redis.setex.assert_not_called()


@patch("requests.get",
       side_effect=requests.RequestException("Network failure"))
def test_file_metadata_network_error(mock_get, client, mock_redis):
    """Test metadata retrieval failure due to network error"""
    mock_redis.get.return_value = None

    response = client.get("/file-metadata")
    assert response.status_code == 500
    assert response.get_json()["error"] == "Network error: Network failure"


@patch("requests.get")
def test_file_metadata_timeout(mock_get, client, mock_redis):
    """Test API timeout handling"""
    mock_redis.get.return_value = None
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"files": []}

    response = client.get("/file-metadata")

    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert kwargs["timeout"] == 10


def test_invalidate_cache_success(client, mock_redis):
    """Test successful cache invalidation"""
    mock_redis.keys.return_value = [
        "file_metadata:public",
        "file_metadata:auth:abc123"
    ]
    mock_redis.delete.return_value = 2

    response = client.post("/file-metadata/invalidate")

    assert response.status_code == 200
    assert response.get_json()["message"] == "Cache invalidated"

    mock_redis.keys.assert_called_once_with("file_metadata:*")
    mock_redis.delete.assert_called_once()


def test_invalidate_cache_no_keys(client, mock_redis):
    """Test cahe invalidation when no keys exist"""
    mock_redis.keys.return_value = []

    response = client.post("/file-metadata/invalidate")

    assert response.status_code == 200
    assert response.get_json()["message"] == "Cache invalidated"

    mock_redis.delete.assert_not_called()


def test_invalidate_cache_redis_error(client, mock_redis):
    """Test cache invalidation with Redis error"""
    mock_redis.keys.side_effect = Exception("Redis connection failed")

    response = client.post("/file-metadata/invalidate")

    assert response.status_code == 500
    assert response.get_json()["error"] == "Cache invalidation failed"


def test_invalidate_cache_no_redis(client):
    """Test cache invalidation when Redis is not available"""
    with patch('v1.routes.file_metadata.get_redis_client', return_value=None):
        response = client.post("/file-metadata/invalidate")

        assert response.status_code == 200
        assert response.get_json()["message"] == "Cache invalidated"


@patch("requests.get")
def test_file_metadata_different_auth_cache_keys(mock_get, client, mock_redis):
    """Test different auth tokens generate different cache keys"""
    mock_redis.get.return_value = None
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"files": []}

    client.get("/file-metadata", headers={"Authorization": "Bearer token1"})
    first_cache_key = mock_redis.get.call_args[0][0]

    mock_redis.reset_mock()

    client.get("/file-metadata", headers={"Authorization": "Bearer token2"})
    second_cache_key = mock_redis.get.call_args[0][0]

    assert first_cache_key != second_cache_key
    assert first_cache_key.startswith("file_metadata:auth")
    assert second_cache_key.startswith("file_metadata:auth")


@patch("requests.get")
def test_file_metadata_cache_ttl(mock_get, client, mock_redis):
    """Test cache TTL is set correctly"""
    mock_redis.get.return_value = None
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"files": ["file1.txt"]}

    client.get("/file-metadata")

    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args[0]
    assert call_args[1] == 300
