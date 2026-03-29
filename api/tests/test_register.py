#!/usr/bin/python3

from flask.testing import FlaskClient
import pytest
from unittest.mock import patch
from v1.app import app


@pytest.fixture
def client():
    """Create a test client for the Flask application"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_register_get(client: FlaskClient):
    """Test GET /register renders the register page"""
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Create Your Account" in response.data


@patch("v1.routes.register.email_exists", return_value=False)
@patch("v1.routes.register.register_user", return_value={"Success": True})
def test_register_post_success(
    mock_register_user,
    mock_email_exists,
    client: FlaskClient
):
    """Test successful user registration returns JSON with redirect URL"""
    response = client.post("/register", data={
        "email": "test@example.com",
        "username": "testuser",
        "password": "SecurePass123!"
    })

    assert response.status_code == 200
    assert response.json["success"]
    assert "redirect_url" in response.json

    with client.session_transaction() as session:
        assert session["verification_email"] == "test@example.com"


@patch("v1.routes.register.email_exists", return_value=True)
def test_register_post_email_exists(mock_email_exists, client: FlaskClient):
    """Test registration with existing email returns 409 status"""
    response = client.post("/register", data={
        "email": "existing@example.com",
        "username": "existinguser",
        "password": "SecurePass123!"
    })
    assert response.status_code == 409
    assert response.json == {"message": "User with email already exists."}


@patch("v1.routes.register.email_exists", return_value=False)
@patch("v1.routes.register.register_user", return_value={"Success": False})
def test_register_post_failure(
    mock_register_user,
    mock_email_exists,
    client: FlaskClient
):
    """Test failed user registration returns 400 status"""
    response = client.post("/register", data={
        "email": "test@example.com",
        "username": "testuser",
        "password": "WeakPass"
    })
    assert response.status_code == 400
    assert response.json == {
        "message": "Registration failed. Please check your inputs."
    }


@patch("v1.routes.register.email_exists", return_value=False)
@patch("v1.routes.register.register_user",
       side_effect=Exception("Cognito error"))
def test_register_post_server_error(
    mock_register_user,
    mock_email_exists,
    client: FlaskClient
):
    """Test server error during registration returns 500 status"""
    response = client.post("/register", data={
        "email": "testuser@example.com",
        "username": "testuser",
        "password": "SecurePass123!"
    })

    assert response.status_code == 500
    assert response.json == {"message": "An error occurred. Please try again."}


@patch("v1.routes.register.email_exists", return_value=False)
@patch("v1.routes.register.register_user", return_value={"Success": True})
def test_register_post_verification_email_in_session(
    mock_register_user,
    mock_email_exists,
    client: FlaskClient
):
    """Test that verification email is properly stored in session"""
    response = client.post("/register", data={
        "email": "test@example.com",
        "username": "testuser",
        "password": "SecurePass123!"
    })

    assert response.status_code == 200

    with client.session_transaction() as session:
        assert "verification_email" in session
        assert session["verification_email"] == "test@example.com"


@patch("v1.routes.register.email_exists", return_value=False)
@patch("v1.routes.register.register_user", return_value={"Success": False})
def test_register_post_missing_username(
    mock_register_user,
    mock_email_exists,
    client: FlaskClient
):
    """Test registration with missing username"""
    response = client.post("/register", data={
        "email": "test@example.com",
        "password": "SecurePass123!"
    })

    assert response.status_code == 400
    assert "message" in response.json


@patch("v1.routes.register.email_exists", return_value=False)
@patch("v1.routes.register.register_user", return_value={"Success": False})
def test_register_post_missing_password(
    mock_register_user,
    mock_email_exists,
    client: FlaskClient
):
    """Test registration with missing password"""
    response = client.post("/register", data={
        "email": "test@example.com",
        "username": "testuser"
    })

    assert response.status_code == 400
    assert "message" in response.json


@patch("v1.routes.register.email_exists", return_value=False)
@patch("v1.routes.register.register_user", return_value={"Success": False})
def test_register_post_missing_email(
    mock_register_user,
    mock_email_exists,
    client: FlaskClient
):
    """Test registration with missing email"""
    response = client.post("/register", data={
        "username": "testuser",
        "password": "SecurePass123!"
    })

    assert response.status_code == 400
    assert "message" in response.json


@patch("v1.routes.register.email_exists", return_value=False)
@patch("v1.routes.register.register_user", return_value={"Success": False})
def test_register_post_empty_data(
    mock_register_user,
    mock_email_exists,
    client: FlaskClient
):
    """Test registration with empty form data"""
    response = client.post("/register", data={
        "email": "",
        "username": "",
        "password": ""
    })

    assert response.status_code == 400
    assert "message" in response.json
