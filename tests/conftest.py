"""
tests/conftest.py
==================
Shared pytest fixtures: a Flask test app using an in-memory SQLite
database (TestingConfig), plus a test client for hitting routes.
"""

from __future__ import annotations

import pytest

from app import create_app
from config import TestingConfig
from utils.extensions import db


@pytest.fixture()
def app():
    """Create a fresh Flask app + in-memory DB for each test."""
    application = create_app(config_object=TestingConfig)
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """A Flask test client bound to the test app."""
    return app.test_client()


@pytest.fixture()
def admin_credentials():
    """The default admin auto-seeded by create_app() in TestingConfig."""
    return {"username": "admin", "password": "Admin@123"}
