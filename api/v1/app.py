import logging
import os
import sys
from datetime import timedelta

from cachelib import SimpleCache
from flask import Blueprint, Flask, render_template, request, session
from flask_cors import CORS
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix

import redis

# ensures these routes are accessible
from v1.config import Config
from v1.routes import file_metadata_bp, upload_bp
from v1.routes.confirm import confirm_bp
from v1.routes.delete import delete_bp
from v1.routes.delete_account import delete_account_bp
from v1.routes.download import download_bp
from v1.routes.health import health_bp
from v1.routes.landing import landing_bp
from v1.routes.login import login_bp
from v1.routes.logout import logout_bp
from v1.routes.main import main_bp
from v1.routes.register import register_bp
from v1.routes.check_file import check_file_bp
from v1.routes.resend_code import resend_bp
from v1.routes.search_file import search_file_bp

logger = logging.getLogger(__name__)

# check if test environment is the current one
is_test = 'pytest' in sys.modules

app = Flask(__name__)

# environment-aware session configuration
environment = os.getenv("ENVIRONMENT", "local")
is_production = environment == "prod"

if is_production:
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1,
    )
    logger.info("ProxyFix middleware enabled for production environment")
    session_cookie_domain = os.getenv(
        'SESSION_COOKIE_DOMAIN', '.filesoncloud.site',
    )
else:
    session_cookie_domain = None

app.secret_key = Config.SECRET_KEY

# set all session configuration
app.config.update(
    SESSION_COOKIE_SECURE=is_production,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
    SESSION_KEY_PREFIX="session:",
    SESSION_COOKIE_DOMAIN=session_cookie_domain,
    SESSION_TYPE="redis" if not is_test else "cachelib",
)

# configure session storage backend
if is_test:
    app.config["SESSION_CACHELIB"] = SimpleCache()
else:
    redis_url = Config.get_redis_url()

    # create Redis client
    redis_client = redis.from_url(
        redis_url,
        decode_responses=False,
        socket_connect_timeout=10,
        socket_timeout=10,
        retry_on_timeout=True,
        health_check_interval=30,
    )

    app.config["SESSION_REDIS"] = redis_client

    if '@' in redis_url:
        display_url = redis_url.split('@')[0]
    else:
        display_url = redis_url.split('://')[1]

    logger.info(
        f"Configured Redis session store with URL: {display_url}@[REDACTED]",
    )

# initialize Session
Session(app)

# base API blueprint
api_bp = Blueprint('api', __name__)
CORS(api_bp,
     origins="*",
     allow_headers=["Content-Type", "Authorization"])

api_bp.register_blueprint(register_bp)
api_bp.register_blueprint(confirm_bp)
api_bp.register_blueprint(resend_bp)
api_bp.register_blueprint(login_bp)
api_bp.register_blueprint(delete_account_bp)
api_bp.register_blueprint(main_bp)
api_bp.register_blueprint(upload_bp)
api_bp.register_blueprint(check_file_bp)
api_bp.register_blueprint(download_bp)
api_bp.register_blueprint(file_metadata_bp)
api_bp.register_blueprint(search_file_bp)
api_bp.register_blueprint(delete_bp)
api_bp.register_blueprint(logout_bp)
api_bp.register_blueprint(landing_bp)
app.register_blueprint(api_bp)
app.register_blueprint(health_bp)


# Error handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


# Test Redis session storage immediately for dev only
with app.app_context():
    if not is_test and os.getenv("ENVIRONMENT") != "prod":
        try:
            redis_client = app.config["SESSION_REDIS"]
            redis_client.ping()

            # flush in dev only
            if os.getenv("ENVIRONMENT") == "local":
                redis_client.flushdb()
                logger.info("Cleared Redis session data")

            # test actual session storage
            test_session_key = "session:test"
            redis_client.setex(test_session_key, 300, b"test_value")
            retrieved = redis_client.get(test_session_key)
            logger.info(
                "Redis session test - stored: test_value, retrieved: "
                f"{retrieved}",
            )

            if retrieved != b"test_value":
                logger.error("Redis session storage not working properly")
            else:
                logger.info("Redis session storage working correctly")

        except Exception as e:
            logger.error(f"Redis session test failed: {e}")


@app.before_request
def log_session_info():
    logger.debug(f"Session before request: {dict(session)}")
    session_id = session.sid if hasattr(session, 'sid') else 'No SID'
    logger.debug(f"Session ID: {session_id}")
    if hasattr(request, 'headers'):
        logger.debug(f"Request headers: {dict(request.headers)}")
    else:
        logger.debug("Request object not available yet")


@app.after_request
def log_session_after_request(response):
    logger.debug(f"Session after request: {dict(session)}")
    if hasattr(response, 'headers'):
        logger.debug(f"Response headers: {dict(response.headers)}")
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
