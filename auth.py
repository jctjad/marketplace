from flask import Blueprint, flash, render_template, redirect, url_for
from flask import request
from models import db, User
from flask_login import login_user, login_required, logout_user
from datetime import datetime
import re

#Auth Blueprint
auth_blueprint = Blueprint('auth', __name__)
email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'

@auth_blueprint.route('/signup', methods = ['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email') #Email acts like our username
        password = request.form.get('password')
        firstName = request.form.get('firstName')
        lastName = request.form.get('lastName')

        #Checking if information is valid
        if not re.match(email_regex, email):
            flash("Please enter a valid email address", "error")
            return redirect(url_for('auth.signup'))

        #Checking if User already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return redirect(url_for('auth.login'))
        
        #Creating a new User
        new_user = User(email=email, first_name=firstName, last_name=lastName, date_created=datetime.today())
        new_user.set_password(password)

        #Add and commite new user to db
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('auth.login'))
    return render_template('signup.html')


@auth_blueprint.route('/login', methods = ['GET', 'POST'])
def login():
    #Doesn't account for how many times someone can log in
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.goto_browse_items_page')) #I believe it's main.index to render index.html
        
    return render_template('login.html')

@auth_blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

