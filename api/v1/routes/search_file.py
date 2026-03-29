import requests
import logging
from . import file_metadata_bp
from v1.config import Config
from flask import jsonify, request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AWS_API_GATEWAY_FETCH_METADATA_URL = Config.AWS_API_GATEWAY_FETCH_METADATA_URL


@file_metadata_bp.route("/search-files", methods=["GET"])
def search_files():
    """
    search for files by name

    GET:
        - Requires a 'search' query parameter
        - Calls Amazon API Gateway to fetch matching file metadata
        - Handles network errors and API failures gracefully

    Returns:
        JSON response:
            - 400 Bad Request: search term is missing
            - 200 OK: search results successful
            - 500 Internal Server Error: API or network failures
    """

    search_term = request.args.get('search', '')
    if not search_term:
        return jsonify({
            "error": "Search term is required"
        }), 400

    try:
        if not AWS_API_GATEWAY_FETCH_METADATA_URL:
            logger.error("Missing API Gateway URL configuration.")
            return jsonify(
                {"error": "Server misconfiguration: missing API URL."}
            ), 500

        headers = {}
        auth_header = request.headers.get("Authorization")
        if auth_header:
            headers["Authorization"] = auth_header

        params = {"search": search_term}
        response = requests.get(
            AWS_API_GATEWAY_FETCH_METADATA_URL,
            params=params,
            headers=headers
        )

        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({
                "error": f"failed to search files: {response.text}"
            }), response.status_code
    except requests.RequestException as e:
        return jsonify({"error": f"Network error: {str(e)}"}), 500
