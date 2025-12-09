import os
from datetime import datetime
from flask import (Blueprint, current_app, flash, redirect, render_template, request, url_for)
from flask_login import login_required, login_user, logout_user
from authlib.integrations.base_client.errors import OAuthError
from website.extensions import db
from .models import User

#Auth Blueprint
auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/signup', methods = ['GET', 'POST'])
def signup():
    """
    This function handles route to login page.
    """
    return render_template('login.html')

@auth_blueprint.route('/login', methods = ['GET', 'POST'])
def login():
    """
    This function handles route to login page.
    """
    return render_template('login.html')

@auth_blueprint.route('/logout')
@login_required
def logout():
    """
    This function handles when a user logs out.
    """
    logout_user()
    return redirect(url_for('auth.login'))

# ===========
# GOOGLE AUTH
# ===========

@auth_blueprint.route("/login/google/")
def login_google():
    """
    This function creates the login for Google.
    """
    google = current_app.config["GOOGLE_CLIENT"]
    try:
        # External window pop up to authorize
        redirect_uri = url_for('auth.authorize_google', _external = True)
        # Redirecting authorize to page url on google cloud project
        return google.authorize_redirect(redirect_uri, prompt = "select_account")
    except Exception as e:
        current_app.logger.error(f"Error During Login:{str(e)}")
        return {"error": "Error occurred during login"}, 400

@auth_blueprint.route("/login/google/callback")
def authorize_google():
    """This function uses Google to authorize the user before they
    can login. 
    If authorized, they are sent to the browse item page.
    Otherwise, they must not be using a valid Colby email.
    """
    google = current_app.config["GOOGLE_CLIENT"]

    error = request.args.get("error")
    if error:
        flash("Google Login canceled or failed", "error")
        return redirect(url_for("auth.login"))

    try:
        token = google.authorize_access_token()
        current_app.logger.info(f"Token received: {token}")
    except OAuthError as e:
        current_app.logger.error(f"OAuthError: {e.error} - {e.description}")
        flash(f"Google Login Failed: {e.error} - {e.description}", "error")
        return redirect(url_for("auth.login"))

    try:
        user_info_endpoint = google.server_metadata.get('userinfo_endpoint')
        resp = google.get(user_info_endpoint)
        user_info = resp.json()
    except Exception as e:
        current_app.logger.error(f"Fetching user info failed: {str(e)}")
        return {"error": "Failed to fetch user info"}, 500

    email = user_info.get('email')
    first_name = user_info.get('given_name', "")
    last_name = user_info.get('family_name', "")

    if not email or not email.endswith("@colby.edu"):
        return {"error": "Access restricted to Colby students."}, 403

    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, first_name=first_name, last_name=last_name)
            # Generate a random password hash
            random_password = os.urandom(16).hex()  # 16 bytes → 32 hex characters
            user.set_password(random_password)
            db.session.add(user)
            db.session.commit()
    except Exception as e:
        current_app.logger.error(f"DB error: {str(e)}")
        return {"error": "Internal server error"}, 500

    try:
        login_user(user)
    except Exception as e:
        current_app.logger.error(f"Login failed: {str(e)}")
        return {"error": "Login failed"}, 500

    return redirect(url_for('main.goto_browse_items_page'))
