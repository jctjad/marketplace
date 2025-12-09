import os
from datetime import datetime
from flask import (Blueprint, current_app, flash, redirect, render_template, request, url_for)
from flask_login import login_required, login_user, logout_user
from authlib.integrations.base_client.errors import OAuthError
from website.extensions import db
from .models import User

#Trying to figure out if this works here or in __init__
# from flask_limiter import limiter
# from flask_limiter.util import get_remote_address


#Auth Blueprint
auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/signup', methods = ['GET', 'POST'])
def signup():
    """
    This function handles when a user is signing up.
    """
    if request.method == 'POST':
        email = request.form.get('email') #Email acts like our username
        password = request.form.get('password')
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')

        #Restricting to Colby emails
        if not email.endswith("@colby.edu"):
            flash("Access Restricted to Colby Students", category="error")
            return render_template('signup.html'), 200

        #Checking if User already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("User already exists", category = "error")
            return render_template('signup.html'), 200

        #Creating a new User
        new_user = User(email=email, first_name=first_name, last_name=last_name,
                        date_created=datetime.today())
        new_user.set_password(password)

        #Add and commite new user to db
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('auth.login'))
    return render_template('signup.html'), 200


@auth_blueprint.route('/login', methods = ['GET', 'POST'])
def login():
    """
    This function handles when a user is trying to log in.
    """
    #Doesn't account for how many times someone can log in
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        #Restricting to Colby emails
        if not email.endswith("@colby.edu"):
            flash("not valid email address", category = "error")
            return render_template('login.html'), 200

        user = User.query.filter_by(email=email).first()
        #Checks if user is in db
        if user: #User in db
            if user.check_password(password):
                login_user(user)
                return redirect(url_for('main.goto_browse_items_page'))
            else:
                flash("Invalid password", category="error")
                return render_template('login.html')
        else: #User is not in db
            flash("Invalid email", category = "error")
            return render_template('login.html')
    return render_template('login.html'), 200

@auth_blueprint.route('/logout')
@login_required
def logout():
    """
    This function handles when a user logs out.
    """
    logout_user()
    return redirect(url_for('auth.login')), 200


# =====================================================
# GOOGLE AUTH
# =====================================================


#Check if this works, might not due to redirect url from google cloud side
#Creating login for google
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
        return {"error": "Error occurred during login"}, 400


@auth_blueprint.route("/login/google/callback")
def authorize_google():
    """This function uses Google to authorize the user before they
    can login. 
    If authorized, they are sent to the browse item page.
    Otherwise, they must not be using a valid Colby email.
    """
    google = current_app.config["GOOGLE_CLIENT"]

    #
    error = request.args.get("error")
    if error:
        flash("Google Login canceled or failed", "error")
        return redirect(url_for("auth.login"))

    #receiving authorize access token
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
        flash("Failed to fetch user info", category = "error")
        return render_template('login.html')

    email = user_info.get('email')
    first_name = user_info.get('given_name', "")
    last_name = user_info.get('family_name', "")

    if not email or not email.endswith("@colby.edu"):
        flash("Access restricted to Colby Students", category = "error")
        return render_template('login.html')

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
        flash("Internal server error", category = "error")
        return render_template('login.html')

    try:
        login_user(user)
    except Exception as e:
        current_app.logger.error(f"Login failed: {str(e)}")
        flash("Login failed", category = "Error")
        return render_template('login.html')

    return redirect(url_for('main.goto_browse_items_page'))