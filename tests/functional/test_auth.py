"""
test_auth.py - Handles Tests for authentication routes in Auth.py
"""

from authlib.integrations.base_client.errors import OAuthError
import website.auth as auth_module
from website import db
from website.models import User

# ============================
# (1) basic tests (page loads)
# ============================

def test_signup_page(test_client):
    """Testing Signup Page"""
    resp = test_client.get("/signup")
    assert resp.status_code == 200
    assert b"Sign in With Google" in resp.data

def test_login_page(test_client):
    """Testing login page"""
    resp = test_client.get("/login")
    assert resp.status_code == 200
    assert b"Sign in With Google" in resp.data

def test_logout_with_logged_in_user(test_client, app):
    """Testing logout functionality"""
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
    """Testing google login success"""
    resp = test_client.get("/login/google/")
    assert resp.status_code == 302
    assert "https://accounts.google.com" in resp.location

def test_login_google_exception(test_client, fake_google):
    """
    Testing google login exception
    Force an exception inside login_google by overriding authorize_redirect
    """
    def boom(redirect_uri, prompt=None):
        raise Exception("boom")

    fake_google.authorize_redirect = boom

    resp = test_client.get("/login/google/")

    #Checking redirect
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"] == "Error during Login. Please try again"

# ===================================
# (3) authorize_google() branch tests
# ===================================

def test_google_valid_email(test_client, fake_google, app):
    """Testing google login with VALID Colby email"""
    fake_google.userinfo_to_return = {
        "email": "newstudent@colby.edu",    # Valid Colby email
        "given_name": "New",
        "family_name": "Student",
    }
    resp = test_client.get("/login/google/callback", follow_redirects=False)
    assert resp.status_code == 302
    assert "/" in resp.location

def test_google_invalid_email(test_client, fake_google):
    """Testing google login with INVALID non-Colby email"""
    fake_google.userinfo_to_return = {
        "email": "user@gmail.com",  # Non-Colby email
        "given_name": "Test",
        "family_name": "User",
    }
    resp = test_client.get("/login/google/callback")
    assert resp.status_code == 302
    assert "/login?error=Access+restricted+to+Colby+Students" in resp.location

def test_google_denied_error(test_client, fake_google):
    """Testing google login accessed denied error"""
    resp = test_client.get("/login/google/callback?error=access_denied")
    assert resp.status_code == 302
    # The redirect should go to login page with error param
    assert "/login?error=Google+login+canceled+or+failed" in resp.location

def test_google_oauth_error(test_client, fake_google):
    """Simulate OAuth error → redirect with error"""
    fake_google.raise_on_token = OAuthError(
        error="invalid_grant",
        description="Bad code",
    )
    resp = test_client.get("/login/google/callback")
    assert resp.status_code == 302
    assert "/login?error=Google+Login+Failed" in resp.location

def test_google_userinfo_error(test_client, fake_google):
    """Testing google login userinfo error"""
    fake_google.userinfo_to_return = {}
    fake_google.raise_on_get = Exception("fetch failed")
    resp = test_client.get("/login/google/callback")
    assert resp.status_code == 302
    assert "/login?error=Failed+to+fetch+user+info" in resp.location

def test_google_existing_user_reused(test_client, fake_google, app):
    """Testing google login with reused user"""
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

    resp = test_client.get("/login/google/callback")
    assert resp.status_code == 302
    assert "/" in resp.location

def test_google_db_error(test_client, fake_google, app, monkeypatch):
    """
    Testing google login db error
    Force db.session.commit() to raise an exception
    """
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
        assert resp.status_code == 302
        assert "/login?error=Internal+server+error" in resp.location


def test_google_login_error(test_client, fake_google, app, monkeypatch):
    """Testing google login error --> ogin_user() fail"""
    fake_google.userinfo_to_return = {
        "email": "loginerr@colby.edu",
        "given_name": "Login",
        "family_name": "Error",
    }
    def bad_login_user(user):
        raise Exception("login failed")
    monkeypatch.setattr(auth_module, "login_user", bad_login_user)

    resp = test_client.get("/login/google/callback")
    assert resp.status_code == 302
    assert "/login?error=Login+failed" in resp.location
