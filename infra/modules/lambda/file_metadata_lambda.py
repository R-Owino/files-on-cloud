"""
fetches a file metadata from the documents table
scans the documents table to get a searched file
supports both authenticated and unauthenticated requests
"""

import boto3
import simplejson as json
import os
import logging
import requests
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError


logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["DYNAMODB_TABLE_NAME"]
REGION = os.environ["REGION"]
COGNITO_USER_POOL_ID = os.environ["COGNITO_USERPOOL_ID"]


def get_cognito_public_keys():
    """fetch Cognito public keys for JWT authentication"""
    try:
        if not COGNITO_USER_POOL_ID:
            logger.warning("Cognito userpool not set")
            return None

        keys_url = (
            f"https://cognito-idp.{REGION}.amazonaws.com/"
            f"{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
        )
        response = requests.get(keys_url)
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching Cognito public keys: {e}")
        return None


def validate_cognito_token(token):
    """Validates Cognito JWT token"""
    try:
        if token.startswith('Bearer '):
            token = token[7:]

        # get the public keys
        jwks = get_cognito_public_keys()
        if not jwks:
            return None

        # decode token header to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')

        key = None
        for jwk in jwks['keys']:
            if jwk['kid'] == kid:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                break

        if not key:
            return None

        # verify the token
        decoded = jwt.decode(
            token,
            key,
            algorithms=['RS256'],
            audience=None,
            options={"verify_aud": False}
        )

        return decoded

    except (InvalidTokenError, ExpiredSignatureError) as e:
        logger.info(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return None


def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # check for auth header - fix for None headers
        headers = event.get('headers') or {}
        auth_header = (
            headers.get('Authorization') or
            headers.get('authorization')
        )

        user_info = None
        if auth_header:
            try:
                user_info = validate_cognito_token(auth_header)
                if user_info:
                    logger.info(
                        f"Authenticted user: {user_info.get('sub', 'unknown')}"
                    )
                else:
                    logger.info("Invalid or expired token provided")
            except Exception as e:
                logger.error(f"Token validation failed: {e}")
        else:
            logger.info("No authorization header, treating as unauthenticated")

        # extract query parameters
        query_params = event.get('queryStringParameters') or {}
        search_term = query_params.get('search', '')
        limit = int(query_params.get('limit', 0))

        # scan the table for the files
        table = dynamodb.Table(TABLE_NAME)
        response = table.scan()
        files = response.get("Items", [])

        logger.info(f"Files received: {len(files)}")

        # extract file metadata
        extracted_files = []
        for file in files:
            file_data = {
                "file_name": file.get("file_name", "unknown"),
                "file_key": file.get("file_key", ""),
                "upload_timestamp": (
                    file.get(
                        "upload_timestamp", "1970-01-01T00:00:00.000000+00:00"
                    )
                ),
                "size_bytes": file.get("size_bytes", 0)
            }

            # only for authenticated users
            if user_info:
                file_data["object_url"] = file.get("object_url", "")

            extracted_files.append(file_data)

        # sort the files by upload timestamp
        sorted_files = sorted(
            extracted_files,
            key=lambda x: x["upload_timestamp"],
            reverse=True
        )

        # apply search filter if search term exists
        if search_term:
            sorted_files = [
                file for file in sorted_files
                if search_term.lower() in file["file_name"].lower()
            ]

        # apply specified limit
        if limit > 0:
            sorted_files = sorted_files[:limit]

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': json.dumps({
                'message': 'Success',
                'files': sorted_files,
                'authenticated': user_info is not None
            })
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }
