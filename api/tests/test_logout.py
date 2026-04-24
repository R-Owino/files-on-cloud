#!/usr/bin/python3

import pytest
from v1.app import app


@pytest.fixture
def client():
    """Create a test client for the Flask application"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_logout(client):
    """Test GET /logout clears session and redirects to landing"""
    with client.session_transaction() as session:
        session["email"] = "testuser@example.com"
        session["logged_in"] = True

    response = client.get("/logout")

    assert response.status_code == 302
    assert "/" in response.location

    with client.session_transaction() as session:
        assert "email" not in session
        assert "logged_in" not in session


def test_logout_post_method(client):
    """Test POST /logout also works"""
    with client.session_transaction() as session:
        session["email"] = "test@example.com"

    response = client.post("/logout")
    assert response.status_code == 302


def test_logout_empty_session(client):
    """Test logout works when session is already empty"""
    response = client.get("/logout")
    assert response.status_code == 302
    assert "/" in response.location


def test_logout_partial_session(client):
    """Test logout clears session with mixed data"""
    with client.session_transaction() as session:
        session["email"] = "test@example.com"
        session["other_data"] = "value"

    client.get("/logout")

    with client.session_transaction() as session:
        assert "email" not in session
        assert "other_data" not in session


def test_logout_cache_headers(client):
    """Test logout response has proper cache headers"""
    response = client.get("/logout")
    assert 'no-cache' in response.headers.get('Cache-Control', '')
