#!/usr/bin/python3

from flask.testing import FlaskClient
import pytest
from v1.app import app


@pytest.fixture
def client():
    """Create a test client for the Flask application"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_main_get_unauthenticated(client: FlaskClient):
    """Test GET /main renders template when not logged in"""
    response = client.get("/main")
    assert response.status_code == 200
    assert b"testuser@example.com" not in response.data


def test_main_get_authenticated(client: FlaskClient):
    """Test GET /main renders template when logged in"""
    with client.session_transaction() as session:
        session["logged_in"] = True
        session["email"] = "testuser@example.com"
    response = client.get("/main")
    assert response.status_code == 200
    assert b"testuser@example.com" in response.data


def test_main_post_unauthenticated(client: FlaskClient):
    """Test POST /main renders template when not logged in"""
    response = client.post("/main")
    assert response.status_code == 200
    assert b"testuser@example.com" not in response.data


def test_main_post_authenticated(client: FlaskClient):
    """Test POST /main renders template when logged in"""
    with client.session_transaction() as session:
        session["logged_in"] = True
        session["email"] = "testuser@example.com"
    response = client.post("/main")
    assert response.status_code == 200
    assert b"testuser@example.com" in response.data
