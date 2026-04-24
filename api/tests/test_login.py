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


def test_login_get(client: FlaskClient):
    """Test GET /login renders the login page."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Welcome Back" in response.data


@patch("v1.routes.login.login_user", return_value={
    "Success": True,
    "tokens": {
        "access_token": "mock_access",
        "id_token": "mock_id",
        "refresh_token": "mock_refresh",
    },
})
def test_login_post_success(mock_login_user, client: FlaskClient):
    """Test successful user login redirects to main page"""
    response = client.post("/login", data={
        "email": "testuser@example.com",
        "password": "SecurePass123!",
    })

    assert response.status_code == 302
    assert "/main" in response.location

    with client.session_transaction() as session:
        assert session["email"] == "testuser@example.com"
        assert session["access_token"] == "mock_access"
        assert session["id_token"] == "mock_id"
        assert session["refresh_token"] == "mock_refresh"
        assert session["logged_in"] is True


@patch("v1.routes.login.login_user", return_value={
    "Success": False,
    "message": "Invalid credentials."},
)
def test_login_post_failure(mock_login_user, client: FlaskClient):
    """Test failed user login re-renders login page"""
    response = client.post("/login", data={
        "email": "testuser@example.com",
        "password": "WrongPass",
    })

    assert response.status_code == 401


@patch("v1.routes.login.login_user", return_value={
    "Success": False,
    "message": "User not found. Please check your credentials.",
})
def test_login_post_user_not_found(mock_login_user, client: FlaskClient):
    """Test failed user login with user not found"""
    response = client.post("/login", data={
        "email": "nonexistent@example.com",
        "password": "SecurePass123!",
    })

    assert response.status_code == 404


def test_login_post_missing_email(client: FlaskClient):
    """Test login attempt with missing email field"""
    response = client.post("/login", data={
        "password": "SecurePass123!",
    })

    assert response.status_code == 400


def test_login_post_missing_password(client: FlaskClient):
    """Test login attempt with missing password field"""
    response = client.post("/login", data={
        "email": "testuser@example.com",
    })

    assert response.status_code == 400


@patch("v1.routes.login.login_user", return_value={
    "Success": True,
    "tokens": {
        "access_token": "mock_access",
        "id_token": "mock_id",
        "refresh_token": "mock_refresh",
    },
})
def test_login_session_timeout_config(mock_login_user, client: FlaskClient):
    """Test that session is configured to be permanent"""
    response = client.post("/login", data={
        "email": "testuser@example.com",
        "password": "SecurePass123!",
    })

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session.permanent is True


@patch("v1.routes.login.login_user", side_effect=Exception("Unexpected error"))
def test_login_unexpected_error(mock_login_user, client: FlaskClient):
    """Test handling of unexpected error during login"""
    response = client.post("/login", data={
        "email": "testuser@example.com",
        "password": "SecurePass123!",
    })

    assert response.status_code == 500
