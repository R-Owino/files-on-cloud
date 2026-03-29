from flask import (Blueprint,
                   render_template,
                   request,
                   redirect,
                   url_for,
                   session
                   )
from v1.cognito import login_user
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define Blueprint for login route
login_bp = Blueprint("login", __name__)


@login_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Handle user login

    GET:
        - Render the login page

    POST:
        - Retrieve email and password from form data
        - Call Cognito to authenticate the user
        - If authentication is successful:
            - store user session details including tokens
            - redirect to the main page
        - If authentication fails:
            - re-render the login page

    Returns:
        JSON response:
            - 200 OK: login page is rendered
            - 302 Redirect: main page upon successful login
    """

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            logger.warning("Login attempt with missing credentials")
            return render_template("login.html"), 400

        logger.debug(f"Login attempt for email: {email}")

        try:
            result = login_user(email, password)
            # logger.info(f"Login result: {result}")

            if result["Success"]:
                session.permanent = True
                session["email"] = email
                session["access_token"] = result["tokens"]["access_token"]
                session["id_token"] = result["tokens"]["id_token"]
                session["refresh_token"] = result["tokens"]["refresh_token"]
                session["logged_in"] = True
                session.modified = True

                return redirect(url_for("api.main.main"))
            else:
                logger.error(f"Login failed: {result['message']}")
                if result["message"] == (
                    "User not found. Please check your credentials."
                ):
                    return render_template("login.html"), 404
                elif result["message"] == "Invalid credentials.":
                    return render_template("login.html"), 401
                else:
                    return render_template("login.html"), 500
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
            return render_template("login.html"), 500

    return render_template("login.html")
