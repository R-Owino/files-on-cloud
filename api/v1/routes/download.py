import os
import boto3
import json
import time
import logging
import requests
from datetime import datetime, timezone, timedelta
from v1.config import Config
from urllib.parse import unquote_plus
from botocore.exceptions import ClientError
from flask import Blueprint, jsonify, request, session, Response
from botocore.signers import CloudFrontSigner
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# Define Blueprint for file upload route
download_bp = Blueprint("download", __name__)

CLOUDFRONT_DOMAIN = Config.CLOUDFRONT_DOMAIN
KEY_PAIR_ID = Config.CLOUDFRONT_PUBLIC_KEY_ID
PRIVATE_KEY_PATH = os.path.join(os.path.dirname(__file__), "private_key.pem")

s3 = boto3.client("s3")
BUCKET_NAME = Config.S3_BUCKET_NAME


def load_private_key():
    """
    Load a private key from a specified file path

    Returns:
        The loaded private key

    Raises:
        FileNotFoundError: File key not found at either path
        Exception: There is an error loading the private key
    """
    key_path = PRIVATE_KEY_PATH

    try:
        with open(key_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None,
                backend=default_backend,
            )
            test_message = b"test"
            signature = (
                private_key.sign(
                    test_message, padding.PKCS1v15(), hashes.SHA1(),
                )
            )
            logger.info(
                "Private key loaded and tested successfully, "
                f"signature length: {len(signature)}",
            )
            return private_key

    except FileNotFoundError as e:
        logger.error(f"Private key file not found at {key_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading private key from {key_path}: {e}")
        raise


private_key = load_private_key()


# signer function
def rsa_signer(message):
    """
    Signs a message using the loaded private key

    Args:
        message: The message to be signed

    Returns:
        The signature of the message using the private key
    """
    return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())


cloudfront_signer = CloudFrontSigner(KEY_PAIR_ID, rsa_signer)


def wait(file_key, max_retries=5, delay=3):
    """
    Wait for file to be accessible in S3 before generating the URL

    Args:
        file_key: The key of the file in S3
        max_retries: Max number of retries to check for the file's availability
        delay: Delay, in seconds, between retries

    Returns:
        bool: True if the file is found and accessible, False otherwise
    """
    for _ in range(max_retries):
        try:
            s3.head_object(
                Bucket=BUCKET_NAME,
                Key=file_key,
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                time.sleep(delay)
            else:
                return False
    return False


def generate_download_url(file_key):
    """
    Helper function to generate a signed URL for a file

    Args:
        file_key: The key of the file in S3

    Returns:
        tuple:
            - signed_url: The signed URL (CloudFront or S3)
            - file_name: The original file name
            - error: An error message if something goes wrong
            - status_code: The HTTP status code indicating the result
    """
    try:
        # extract the original file name
        file_name = file_key.split('/')[1]

        # check if the file exists in the bucket
        try:
            s3.head_object(
                Bucket=BUCKET_NAME,
                Key=file_key,
            )
        except ClientError as e:
            error_code = e.response["Error"]["Code"]

            if error_code == "404":
                logger.warning(f"File not found in S3: {file_key}")
                return None, None, "File not found", 404

            if error_code == "403":
                logger.error(f"Access denied to file: {file_key}")
                return None, None, "Access denied", 403

            logger.error(f"S3 error: {error_code} - {str(e)}")
            return None, None, "An unexpected error occured", 500

        # generate a CloudFront URL and set expiration date
        cloudfront_url = f"https://{CLOUDFRONT_DOMAIN}/{file_key}"
        expires = datetime.now(timezone.utc) + timedelta(hours=1)

        if not wait(file_key):
            return None, None, "File not found or not yet available", 404

        # generate a signed url
        try:
            # custom policy for CloudFront Key Groups
            policy = {
                "Statement": [
                    {
                        "Resource": cloudfront_url,
                        "Condition": {
                            "DateLessThan": {"AWS:EpochTime": int(expires.timestamp())}  # noqa E501
                        },
                    },
                ],
            }

            # Generate signed URL using the custom policy
            signed_url = cloudfront_signer.generate_presigned_url(
                cloudfront_url,
                policy=json.dumps(policy),
            )

            logger.info(f"CloudFront URL: {cloudfront_url}")
            logger.info(f"Generated signed URL: {signed_url}")
            logger.info(f"Key Pair ID being used: {KEY_PAIR_ID}")

            return signed_url, file_name, None, 200

        except Exception as e:
            logger.error(f"Error generating CloudFront signed URL: {str(e)}")
            try:
                presigned_url = s3.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": BUCKET_NAME,
                        "Key": file_key,
                        "ResponseContentDisposition": (
                            f'attachment; filename="{file_name}"'
                        ),
                    },
                    ExpiresIn=3600,
                )
                logger.warning("Falling back to S3 pre-signed URL")
                return presigned_url, file_name, None, 200
            except ClientError as e:
                logger.error(f"Error generating S3 pre-signed URL: {str(e)}")
                return None, None, "Failed to generate download URL", 500

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return None, None, "An unexpected error occured", 500


@download_bp.route("/download", methods=["GET"])
def download_file():
    """
    Generate a pre-signed URL for downloading a file from S3 or CloudFront

    GET:
        - Requires user authentication
        - Requires a `file_key` query parameter specifying the file to download
        - Calls S3 to verify the file exists
            before generating the pre-signed URL
        - Handles missing files, access errors and unexpected failures

    Returns:
        JSON response:
            - 401 Unauthorized: user not logged in
            - 400 Bad Request: `file_key` is missing
            - 200 OK: pre-signed URL generated successfully
            - 404 Not Found: file does not exist in S3
            - 403 Forbidden: access to the file is denied
            - 500 Internal Server Error: S3 errors and unexpected failures
    """
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        file_key = unquote_plus(request.args.get("file_key", ""))

        if not file_key:
            logger.info("Missing file key")
            return jsonify({
                "error": "Missing required parameter: file_key",
            }), 400

        signed_url, file_name, error, status_code = (
            generate_download_url(file_key)
        )

        if error:
            return jsonify({"error": error}), status_code

        return jsonify({
            "presigned_url": signed_url,
            "file_name": file_name,
        }), 200

    except Exception as e:
        logger.error(f"An error occured: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@download_bp.route("/download/<path:file_key>", methods=["GET"])
def proxy_download(file_key):
    """
    Proxy endpoint to hide the CloudFront/S3 URL

    Args:
        file_key: The key of the file in S3

    Returns:
        Response: A streaming response that redirects the user
                    to the signed URL

    Raises:
        JSON response:
            - 401 Unauthorized: user not logged in
            - 404 Not Found: file does not exist in S3
            - 500 Internal Server Error: failed to fetch the file
                or generate the URL
    """
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    file_key = unquote_plus(file_key)
    signed_url, file_name, error, status_code = generate_download_url(file_key)

    if error:
        logger.error(f"Failed to generate signed URL: {error}")
        return jsonify({
            "error": error,
        }), status_code

    try:
        # Stream the file from CloudFront
        response = requests.get(signed_url, stream=True)

        if response.status_code != 200:
            return jsonify({
                "error": (
                    f"Failed to fetch file"
                    f"(Status: {response.status_code})"
                ),
            }), response.status_code

        return Response(
            response.iter_content(chunk_size=8192),
            content_type=response.headers["Content-Type"],
            headers={
                "Content-Disposition": f'attachment; filename="{file_name}"',
                "Content-Length": response.headers.get("Content-Length"),
            },
        )
    except requests.RequestException as e:
        logger.error(f"Request error when fetching file: {str(e)}")
        return jsonify({"error": "Failed to fetch file"}), 500
