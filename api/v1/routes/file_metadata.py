import hashlib
import json
import logging

import requests
from flask import current_app, jsonify, request

from flask import Blueprint

from v1.config import Config

file_metadata_bp = Blueprint("file_metadata", __name__)

logger = logging.getLogger(__name__)

AWS_API_GATEWAY_FETCH_METADATA_URL = Config.AWS_API_GATEWAY_FETCH_METADATA_URL


def get_redis_client():
    """Get Redis client from Flask session config"""
    return current_app.config.get("SESSION_REDIS")


def generate_cache_key(auth_header):
    """Generate cache key based on auth status"""
    if auth_header:
        auth_hash = hashlib.md5(auth_header.encode()).hexdigest()[:8]
        return f"file_metadata:auth{auth_hash}"
    else:
        return "file_metadata:public"


@file_metadata_bp.route("/file-metadata", methods=["GET"])
def file_metadata():
    """
    Fetch recent file metadata from documents DynamoDB table
    via API gateway with a limit. Use Redis for caching performance.

    Cache strategy:
        - Separate cache keys for authenticated and guest users
        - 5 minute TTL for recent files
        - Cche invalidation on file uploads

    Returns:
        - 200 OK: file metadata retrieval successful
        - 500 Internal Server Error: API or network failures
    """

    try:
        if not AWS_API_GATEWAY_FETCH_METADATA_URL:
            logger.error("Missing API Gateway URL configuration.")
            return jsonify(
                {"error": "Server misconfiguration: missing API URL."},
            ), 500

        redis_client = get_redis_client()

        # generate cache key based on auth status
        auth_header = request.headers.get("Authorization")
        cache_key = generate_cache_key(auth_header)

        # try the redis client first
        if redis_client:
            try:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    logger.info(f"Cache hit for key: {cache_key}")
                    return jsonify(json.loads(cached_data)), 200
            except Exception as e:
                logger.warning(f"Cache read error: {e}")

        logger.info(f"Cache miss for key: {cache_key}")

        # forward client's auth status
        headers = {}
        auth_header = request.headers.get("Authorization")
        if auth_header:
            headers["Authorization"] = auth_header

        params = {"limit": 15}
        response = requests.get(
            AWS_API_GATEWAY_FETCH_METADATA_URL,
            params=params,
            headers=headers,
            timeout=10,
        )

        if response.status_code == 200:
            response_data = response.json()

            # cache successful response for 300s
            if redis_client:
                try:
                    redis_client.setex(
                        cache_key,
                        300,
                        json.dumps(response_data),
                    )
                    logger.info(f"Cached response for key: {cache_key}")
                except Exception as e:
                    logger.warning(f"Cache write error:{e}")
            return jsonify(response_data), 200
        else:
            return jsonify({
                "error": f"Failed to fetch files: {response.text}",
            }), response.status_code
    except requests.RequestException as e:
        logger.error(f"Network error: {str(e)}")
        return jsonify({"error": f"Network error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@file_metadata_bp.route("/file-metadata/invalidate", methods=["POST"])
def invalidate_file_metadata():
    """
    Invalidate file metadata cache when files are uploaded/deleted
    Call this endpoint after file operations
    """
    try:
        redis_client = get_redis_client()
        if redis_client:
            # clear both authenticated and guest user cache
            pattern = "file_metadata:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache keys")
        return jsonify({"message": "Cache invalidated"}), 200
    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")
        return jsonify({"error": "Cache invalidation failed"}), 500
