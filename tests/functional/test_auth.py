# functional tests

from authlib.integrations.base_client.errors import OAuthError
from website import db
from website.models import User
import website.auth as auth_module

# ============================
# (1) basic tests (page loads)
# ============================

def test_signup_page(test_client):
    resp = test_client.get("/signup")
    assert resp.status_code == 200
    assert b"Sign in With Google" in resp.data

def test_login_page(test_client):
    resp = test_client.get("/login")
    assert resp.status_code == 200
    assert b"Sign in With Google" in resp.data

def test_logout_with_logged_in_user(test_client, app):
    with app.app_context():
        user = User(
            email="logouttest@colby.edu",
            first_name="Test",
            last_name="User",
        )
        user.set_password("x")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    # Simulate logged-in user
    with test_client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)

    resp = test_client.get("/logout", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.location

# ============================================
# (2) login_google tests (success + exception)
# ============================================

def test_login_google_success(test_client, fake_google):
    resp = test_client.get("/login/google/")
    assert resp.status_code == 302
    assert "https://accounts.google.com" in resp.location

def test_login_google_exception(test_client, fake_google):
    # Force an exception inside login_google by overriding authorize_redirect
    def boom(redirect_uri, prompt=None):
        raise Exception("boom")

    fake_google.authorize_redirect = boom

    resp = test_client.get("/login/google/")
    assert resp.status_code == 400

# ===================================
# (3) authorize_google() branch tests
# ===================================

def test_google_valid_email(test_client, fake_google, app):
    fake_google.userinfo_to_return = {
        "email": "newstudent@colby.edu",    # Valid Colby email
        "given_name": "New",
        "family_name": "Student",
    }
    resp = test_client.get("/login/google/callback", follow_redirects=False)
    assert resp.status_code == 302
    assert "/" in resp.location     # Redirects to Browse Items page

def test_google_invalid_email(test_client, fake_google):
    fake_google.userinfo_to_return = {
        "email": "user@gmail.com",  # Non-Colby email
        "given_name": "Test",
        "family_name": "User",
    }
    resp = test_client.get("/login/google/callback")
    assert resp.status_code == 403

def test_google_denied_error(test_client, fake_google):
    resp = test_client.get("/login/google/callback?error=access_denied")
    assert resp.status_code == 302
    assert "/login" in resp.location

def test_google_oauth_error(test_client, fake_google):
    fake_google.raise_on_token = OAuthError(
        error="invalid_grant",
        description="Bad code",
    )
    resp = test_client.get("/login/google/callback")
    assert resp.status_code == 302
    assert "/login" in resp.location

def test_google_userinfo_error(test_client, fake_google):
    fake_google.userinfo_to_return = {}
    fake_google.raise_on_get = Exception("fetch failed")
    resp = test_client.get("/login/google/callback")
    assert resp.status_code == 500

def test_google_existing_user_reused(test_client, fake_google, app):
    with app.app_context():
        existing = User(
            email="existing@colby.edu", # Pre-create a user with the same email
            first_name="Old",
            last_name="Name",
        )
        existing.set_password("x")
        db.session.add(existing)
        db.session.commit()
        existing_id = existing.id

    fake_google.userinfo_to_return = {
        "email": "existing@colby.edu",
        "given_name": "New",
        "family_name": "Name",
    }

    resp = test_client.get("/login/google/callback", follow_redirects=False)
    assert resp.status_code == 302

def test_google_db_error(test_client, fake_google, app, monkeypatch):
    # Force db.session.commit() to raise an exception
    fake_google.userinfo_to_return = {
        "email": "dberror@colby.edu",
        "given_name": "DB",
        "family_name": "Error",
    }
    with app.app_context():
        original_commit = db.session.commit
        def bad_commit():
            raise Exception("DB down")
        monkeypatch.setattr(db.session, "commit", bad_commit)
        resp = test_client.get("/login/google/callback")
        assert resp.status_code == 500
        assert resp.is_json
        assert resp.get_json()["error"] == "Internal server error"

def test_google_login_error(test_client, fake_google, app, monkeypatch):
    # login_user() fail
    fake_google.userinfo_to_return = {
        "email": "loginerr@colby.edu",
        "given_name": "Login",
        "family_name": "Error",
    }
    def bad_login_user(user):
        raise Exception("login failed")
    monkeypatch.setattr(auth_module, "login_user", bad_login_user)
    resp = test_client.get("/login/google/callback")
    assert resp.status_code == 500
    assert resp.is_json
    assert resp.get_json()["error"] == "Login failed"