from flask import (Blueprint,
                   redirect,
                   url_for,
                   session,
                   make_response)

# define Blueprint for logout route
logout_bp = Blueprint("logout", __name__)


@logout_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """
    Handle user logout

    - Clears all the session data
    - Redirects the user to the login page

    Returns:
        JSON response:
            - 302 Redirect: login page
    """
    session.clear()
    response = make_response(redirect(url_for("api.landing.landing")))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
