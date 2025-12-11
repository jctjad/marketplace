"""Sets up functional tests"""

import pytest
import os
from website import create_app, db, socketio
from website.models import User, Item
from sqlalchemy.exc import IntegrityError


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
    if you need it. Right now it's effectively a no-op.
    """
    yield

@pytest.fixture
def login_user(test_client, init_database):
    """
    Placeholder login helper fixture. Update this to perform a real login
    once you have a username/password form-based login.
    """
    yield

@pytest.fixture
def authed_client(app, test_client):
    """
    Creates (or reuses) a user, logs them in by setting the Flask-Login
    session key, and returns (client, user).
    """
    with app.app_context():
        user = User.query.filter_by(email="testuser@colby.edu").first()
        if user is None:
            user = User(
                email="testuser@colby.edu",
                first_name="Test",
                last_name="User"
            )
            user.set_password("password")
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                # if another test created it in the meantime
                user = User.query.filter_by(email="testuser@colby.edu").first()

        user_id = user.id

    client = test_client
    with client.session_transaction() as sess:
        # Flask-Login uses this key for the current user
        sess["_user_id"] = str(user_id)

    return client, user


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


@pytest.fixture
def test_socketio_client(app):
    """
    Creates a test client for the socketio client.
    """
    test_client = app.test_client()
    socketio_test_client = socketio.test_client(app, flask_test_client=test_client)

    yield {'socketio_test_client': socketio_test_client, 'socketio': socketio}

    socketio_test_client.disconnect()

@pytest.fixture
def test_data_socketio(test_client):
    """
    Creates a test user and test item for the socketio tests.
    """
    with test_client.application.app_context():
        db.drop_all()
        db.create_all()

        user1 = User(email='test1@colby.edu', first_name='John', last_name='Smith')
        user1.set_password('password1')
        db.session.add(user1)

        db.session.commit()

        item = Item(seller_id=user1.id, name='test_item', description='description for test item',
                    item_photos='placeholder.svg', price=10.0)

        db.session.add(item)
        db.session.commit()

        yield {'user1': user1, 'item': item}

        # db.session.remove()
        # db.drop_all()

        # Instead of drop_all(), just clear rows so other tests still have tables
        db.session.query(Item).delete()
        db.session.query(User).delete()
        db.session.commit()
