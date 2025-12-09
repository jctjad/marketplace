from website import create_app
from website.models import db, User
import os
import pytest
from unittest.mock import patch, MagicMock
from flask import url_for

# =====================================================
# LOGIN/SIGNUP Tests
# =====================================================

def test_login_page(test_client):
    """
    GIVEN a flask application configured for testing
    WHEN the '/login' page is requested through GET
    THEN check if response is valid
    """

    response = test_client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data
    assert b'email' in response.data
    assert b'password' in response.data
    assert b'Google' in response.data #For Google login button


def test_signup_page(test_client):
    """
    GIVEN a flask application configured for testing
    WHEN the '/login' page is requested through GET
    THEN check if response is valid
    """

    response = test_client.get('/signup')
    assert response.status_code == 200
    assert b'Sign Up' in response.data
    assert b'email' in response.data
    assert b'password' in response.data
    assert b'firstName' in response.data
    assert b'lastName' in response.data
    assert b'Google' in response.data #For Google login button


def test_logout(test_client):
    """
    GIVEN Flask app configured for test
    WHEN the '/logout/ page requested (GET)
    THEN check if response valid
    """
    response = test_client.get('/logout', follow_redirects = True)
    assert response.status_code == 200
    assert b'Login' in response.data
    assert b'email' in response.data
    assert b'password' in response.data

# =====================================================
# LOGIN/SIGNUP Fail Tests
# =====================================================

def test_failed_login_domain(test_client):
    """
    GIVEN Flask app configured for test
    WHEN the '/login' page is posted with non-colby email
    THEN check if response is valid
    """

    response = test_client.post('/login', data = dict(email='test@gmail.com', password = "wrongpassword"), follow_redirects = True)
    assert response.status_code == 200
    assert b'Login' in response.data
    assert b'not valid email address' in response.data

def test_failed_login_email_does_not_exist(test_client):
    """
    GIVEN a Flask app configured to test
    WHEN '/login' is posted with incorrect email (POST)
    THEN check if response is valid
    """

    #Making sure test user is in db
    test_client.post(
        '/signup',
        data = dict(
            email = 'student@colby.edu',
            password = 'correctPass',
            firstName = 'Test',
            lastName = 'User'
        ),
        follow_redirects = True
    )

    response = test_client.post('/login', data = dict(email="wrongStudent@colby.edu", password = "correctPass"), follow_redirects = True)
    assert response.status_code ==  200
    assert b'Invalid email' in response.data

def test_failed_login_password(test_client):
    """
    GIVEN Flask app configured for test
    WHEN the '/login' page is posted with wrong password
    THEN check if response is valid
    """

    #Making sure test user is in db
    test_client.post(
        '/signup',
        data = dict(
            email = 'student@colby.edu',
            password = 'correctPass',
            firstName = 'Test',
            lastName = 'User'
        ),
        follow_redirects = True
    )

    response = test_client.post(
        '/login',
        data = dict(email = 'student@colby.edu', password = 'wrongPass'),
        follow_redirects = True
    )

    assert response.status_code == 200
    assert b'Login' in response.data
    assert b'Invalid password' in response.data

def test_failed_signup_email(test_client):
    """
    GIVEN Flask app configured for test
    WHEN the '/signup' page is posted with non-colby email
    THEN check if response is valid
    """

    response = test_client.post('/signup', data = dict(email='test@gmail.com', password = "wrongpassword", firstName = "Test", lastName = "User"), follow_redirects = True)
    assert response.status_code == 200
    assert b'Sign Up' in response.data
    assert b'Access Restricted to Colby Students' in response.data


def test_failed_signup_existing_user(test_client):
    """
    GIVEN Flask app configured to test
    WHEN '/signup' page posted with existing user (POST)
    THEN check if response is valid
    """

    #Making sure test user is in db
    test_client.post(
        '/signup',
        data = dict(
            email = 'student@colby.edu',
            password = 'correctPass',
            firstName = 'Test',
            lastName = 'User'
        ),
        follow_redirects = True
    )

    response = test_client.post('/signup', data = dict(email = 'student@colby.edu', password = 'correctPass', firstName = 'Test', lastName = 'User'), follow_redirects = True)
    assert response.status_code == 200
    assert b'Sign Up' in response.data
    assert b'User already exists' in response.data

# =====================================================
# LOGIN/SIGNUP Success Tests
# =====================================================

def test_successful_login(test_client): #before fix, this didn't have an existing user, so no test case for failure should be if test user doesn't exist in db
    """
    GIVEN a Flask app configured to test
    WHEN '/login' is posted with correct credentials (POST)
    THEN check if response is valid
    """

    #Making sure test user is in db
    test_client.post(
        '/signup',
        data = dict(
            email = 'student@colby.edu',
            password = 'correctPass',
            firstName = 'Test',
            lastName = 'User'
        ),
        follow_redirects = True
    )

    response = test_client.post('/login', data = dict(email="student@colby.edu", password = "correctPass"), follow_redirects = True)
    assert response.status_code ==  200
    assert b'Browse Items' in response.data

def test_successful_signup(test_client, app):
    """
    GIVEN a Flask app configured to test
    WHEN '/signup' is posted with correct credentials to create a new user(POST)
    THEN check if response is valid
    """
    response = test_client.post('/signup', data = dict(email = 'student@colby.edu', password = 'correctPass', firstName = 'Test', lastName = 'User'), follow_redirects = True)
    assert response.status_code == 200
    assert b'Login' in response.data #checks if Login page was redirected
    
    #Checking that user now exists in database
    with app.app_context():
        user = User.query.filter_by(email = 'student@colby.edu').first()
        assert user is not None
        assert user.first_name == "Test"
        assert user.last_name == "User"
    

# =====================================================
# GOOGLE AUTH Tests
# =====================================================

def test_google_login_redirect(test_client):
    """
    GIVEN Flask app configured to test
    WHEN '/login' redirects to google account page(GET)
    THEN check if response is valid
    """

    response = test_client.get('/login/google/')

    assert response.status_code == 302
    assert "accounts.google.com" in response.headers["Location"]


def test_google_login_success(test_client, app):
    """
    GIVEN Google Mock object
    WHEN '/login' redirects to google account page(GET)
    THEN check if response is valid
    """

    #Mocking user info returned by google
    fake_user_info = {
        "email": "student@colby.edu",
        "given_name": "Test",
        "family_name": "User"
    }

    #Replacing current_app in auth.py with mock object
    #Allows to test with fake Google Client
    with patch("website.auth.current_app") as mock_app:
        mock_google = MagicMock() #Fake OAuth Client
        #pretend we obtained an access token
        mock_google.authorize_access_token.return_value = {"access_token": "fake-token"}
        #Pretending userinfo endpoint returned fake user
        mock_resp = MagicMock()
        mock_resp.json.return_value = fake_user_info
        mock_google.get.return_value = mock_resp
        #Pretending google gave us userinfo endpoint URL
        mock_google.server_metadata = {"userinfo_endpoint": "https://fake.endpoint/userinfo"}
        #Inserting fake google client into app.config
        mock_app.config = {"GOOGLE_CLIENT": mock_google}

        # Call the callback route
        response = test_client.get("/login/google/callback")
        
        # It should redirect to browse items page
        assert response.status_code == 302
        assert response.location.endswith("/")


# =====================================================
# GOOGLE AUTH Fail Tests
# =====================================================

def test_google_login_error_param(test_client):
    """
    GIVEN Google Mock object
    WHEN '/login/google/callback' receives error from access denial(GET)
    THEN check if response is valid
    """

    response = test_client.get("/login/google/callback?error=access_denied",
                            follow_redirects=False)
    
    assert response.status_code == 302
    assert response.location.endswith("/login")

# =====================================================
# Rest of the tests were gonna be checking the path for the google callback
# that catches errors 

# Finally I was gonna test how the code handles the information recieved from google
# =====================================================



