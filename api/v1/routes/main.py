import logging
from flask import (Blueprint,
                   render_template,
                   session)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define the Blueprint for the main route
main_bp = Blueprint("main", __name__)


@main_bp.route("/main", methods=["GET", "POST"])
def main():
    """
    Handles requests to the main page

    GET:
        - Display main page for all users (authenticated and unauthenticated)
        - Pass user session data to template for conditional rendering
    POST:
        - Retrieve authenticated user details from session
        - Handle form submissions from main page

    Returns:
        JSON response:
            - 200 OK: render main page content for all users
    """

    is_logged_in = session.get("logged_in", False)
    username = session.get("email", None) if is_logged_in else None

    logger.info(
        f"Main page accessed - Logged in: {is_logged_in}, User: {username}",
    )

    return render_template("main.html",
                           is_logged_in=is_logged_in,
                           username=username)
