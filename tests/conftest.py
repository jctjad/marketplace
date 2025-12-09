"""Sets up functional tests"""

import os
import pytest
from website import create_app, db

@pytest.fixture(scope="session")
def app():
    """
    Create a single Flask app instance for the test session,
    using the TestingConfig and setting up/tearing down the DB.
    """
    os.environ["CONFIG_TYPE"] = "config.TestingConfig"
    flask_app = create_app()

    with flask_app.app_context():
        db.create_all()

    yield flask_app

    with flask_app.app_context():
        db.drop_all()

@pytest.fixture
def test_client(app):
    """
    Per-test client that uses the shared app fixture.
    """
    with app.test_client() as client:
        yield client

@pytest.fixture
def init_database(app, test_client):
    """
    Hook for populating the database before a group of tests,
    if you need it. Right now it’s effectively a no-op.
    """
    yield

@pytest.fixture
def login_user(test_client, init_database):
    """
    Placeholder login helper fixture. Update this to perform a real login
    once you have a username/password form-based login.
    """
    yield

##################
#  Google auth   #
##################

class FakeGoogle:
    """Fake Google client that matches auth.py usage"""
    def __init__(self):
        self.server_metadata = {
            "userinfo_endpoint": "https://fake.example.com/userinfo"
        }
        self.token_to_return = {"access_token": "TOKEN"}
        self.userinfo_to_return = {}
        self.raise_on_token = None
        self.raise_on_get = None

    def authorize_redirect(self, redirect_uri, prompt=None):
        """Authorize redirect"""
        from flask import redirect
        return redirect("https://accounts.google.com/o/oauth2/auth?fake=1")

    def authorize_access_token(self):
        """Authorize access token"""
        if self.raise_on_token:
            raise self.raise_on_token
        return self.token_to_return

    def get(self, url):
        """Getter"""
        if self.raise_on_get:
            raise self.raise_on_get

        class Resp:
            def __init__(self, data):
                self._data = data

            def json(self):
                return self._data

        return Resp(self.userinfo_to_return)

@pytest.fixture
def fake_google(app):
    """
    Attach a FakeGoogle instance to the Flask app's config so that
    auth.py can use current_app.config["GOOGLE_CLIENT"] as normal.
    """
    g = FakeGoogle()
    app.config["GOOGLE_CLIENT"] = g
    return g
