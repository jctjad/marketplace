"""
auth.py - Handles authentication routes for MuleBay site. Includes 
signup, login, logout, and Google OAuth.
"""

import os

from authlib.integrations.base_client.errors import OAuthError
from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, url_for)
from flask_login import login_required, login_user, logout_user

from website.extensions import db

from .models import User

#Auth Blueprint
auth_blueprint = Blueprint('auth', __name__)


@auth_blueprint.route('/signup', methods = ['GET', 'POST'])
def signup():
    """
    This function handles route to login page
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
        #External window pop up to authorize
        redirect_uri = url_for('auth.authorize_google', _external = True)
        #Redirecting authorize to page url on google cloud project
        return google.authorize_redirect(redirect_uri, prompt = "select_account")
    except Exception as e:
        current_app.logger.error(f"Error During Login:{str(e)}")
        return {"error": "Error during Login. Please try again"}, 400

@auth_blueprint.route("/login/google/callback")
def authorize_google():
    google = current_app.config["GOOGLE_CLIENT"]

    # 1. If Google explicitly returns an error
    if (error := request.args.get("error")):
        return redirect(url_for("auth.login", error="Google login canceled or failed"))

    # 2. Get Google token
    try:
        token = google.authorize_access_token()
    except OAuthError as e:
        return redirect(url_for("auth.login", error=f"Google Login Failed: {e.error}"))

    # 3. Fetch Google user info
    try:
        user_info = google.get(google.server_metadata.get("userinfo_endpoint")).json()
    except Exception:
        return redirect(url_for("auth.login", error="Failed to fetch user info"))

    email = user_info.get("email")
    first_name = user_info.get("given_name", "")
    last_name = user_info.get("family_name", "")

    # 4. Restrict to @colby.edu
    if not email or not email.endswith("@colby.edu"):
        return redirect(url_for("auth.login", error="Access restricted to Colby Students"))

    # 5. Create user if needed
    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, first_name=first_name, last_name=last_name)
            user.set_password(os.urandom(16).hex())
            db.session.add(user)
            db.session.commit()
    except Exception:
        return redirect(url_for("auth.login", error="Internal server error"))

    # 6. Log user in
    try:
        login_user(user)
    except Exception:
        return redirect(url_for("auth.login", error="Login failed"))

    # 7. SUCCESS → redirect normally
    return redirect(url_for("main.goto_browse_items_page"))
