"""
tests/test_smoke.py
====================
Basic smoke tests: app boots, health check works, login flow works,
and protected pages redirect when not authenticated.
"""

from __future__ import annotations


def test_api_health_check(client):
    """The unauthenticated health-check endpoint should always return 200."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_dashboard_requires_login(client):
    """Visiting the dashboard while logged out should redirect to the login page."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code in (301, 302)
    assert "/auth/login" in response.headers["Location"]


def test_login_page_loads(client):
    """The login page itself should render without authentication."""
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"Sign In" in response.data


def test_successful_login_redirects_to_dashboard(client, admin_credentials):
    """Logging in with the seeded default admin should succeed and redirect."""
    response = client.post("/auth/login", data=admin_credentials, follow_redirects=False)
    assert response.status_code in (301, 302)
    assert "/dashboard" in response.headers["Location"]


def test_failed_login_shows_error(client):
    """An incorrect password should not log the user in."""
    response = client.post(
        "/auth/login", data={"username": "admin", "password": "wrong-password"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_api_login_returns_jwt(client, admin_credentials):
    """POSTing valid credentials to the JSON API should return a JWT."""
    response = client.post("/api/v1/auth/login", json=admin_credentials)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert isinstance(payload["token"], str) and len(payload["token"]) > 20
