from website import db
import os
from datetime import datetime
from flask import (Blueprint, current_app, flash, redirect, render_template, request, url_for)
from flask_login import login_required, login_user, logout_user
from .models import User
from authlib.integrations.base_client.errors import OAuthError

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
            return {"error": "Access Restricted to Colby Students"}, 400

        #Checking if User already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return redirect(url_for('auth.login'))

        #Creating a new User
        new_user = User(email=email, first_name=first_name, last_name=last_name,
                        date_created=datetime.today())
        new_user.set_password(password)

        #Add and commite new user to db
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('auth.login'))
    return render_template('signup.html')


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
            return {"error": "not valid email address"}, 400

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            #I believe it's main.index to render index.html
            return redirect(url_for('main.goto_browse_items_page'))

    return render_template('login.html')

@auth_blueprint.route('/logout')
@login_required
def logout():
    """
    This function handles when a user logs out.
    """
    logout_user()
    return redirect(url_for('auth.login'))


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



# #Creating authorize for google
# @auth_blueprint.route("/login/google/callback")
# def authorize_google():
#     google = current_app.config["GOOGLE_CLIENT"]

#     #Checking if google returned an error (cancel, denied, etc)
#     error = request.args.get("error")
#     if error:
#         flash("Google Login canceled or failed", "error")
#         return redirect(url_for("auth.login"))


#     #Wrapping token in error net
#     try:
#         token = google.authorize_access_token()
#     except Exception as e: #Catches OAuth specific errors
#         error = request.args.get("error")
#         flash(f"Google Login Failed: {error or e.description}", "error")
#         return redirect(url_for("auth.login"))

#     #Grabbing data needed to create new user

#     userInfo_endpoint = google.server_metadata.get('userinfo_endpoint')
#     resp = google.get(userInfo_endpoint)
#     userInfo = resp.json()

#     #Grabbing user details
#     # email = userInfo['email'] #Grabs email user plugged in
#     email = userInfo.get('email')
#     first_name = userInfo.get('given_name', "")
#     last_name = userInfo.get('family_name', "")

#     if not email.endswith("@colby.edu"):
#         return {"error": "Access restricted to Colby students."}, 403


#     user = User.query.filter_by(email = email).first()
#     if not user: #If we don't have a user
#         user = User(
#             email = email,
#             first_name = first_name,
#             last_name = last_name)
#         #user.set_password(os.urandom(16).hex()) #Random hex pass - google auth doesn't need pass
#         db.session.add(user)
#         db.session.commit()

#     #Logging user into flask-login
#     login_user(user)

#     return redirect(url_for('main.goto_browse_items_page')) #redirects towards dashboard route -
