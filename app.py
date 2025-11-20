import eventlet
eventlet.monkey_patch()

import os
from flask import Flask
from views import main_blueprint, item_blueprint, profile_blueprint
from models import db, User

#Messaging import
from setup_socket import app, socketio

#Auth Libraries
from auth import auth_blueprint
from flask_login import LoginManager

#Cloudinary
import cloudinary

# app = Flask(__name__)

uri = os.getenv("DATABASE_URL")  # Heroku sets this automatically

if uri is None:
    # Local development fallback (SQLite)
    uri = "sqlite:///marketplace.db"

# Fix for Heroku’s old Postgres URLs
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

# Configure Cloudinary
cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET'),
    secure = True # Ensures URLs are HTTPS
)

db.init_app(app)

#Auth Section
login_man = LoginManager(app)
login_man.login_view = 'auth.signup'
login_man.login_message = None

@login_man.user_loader
def load_user(id):
    return User.query.get(int(id))

#Blue Register Section
app.register_blueprint(main_blueprint)
app.register_blueprint(item_blueprint)
app.register_blueprint(profile_blueprint)
app.register_blueprint(auth_blueprint)


if __name__ == '__main__':
    # auto create tables in local dev only
    if uri.startswith("sqlite:///"):
        with app.app_context():
            db.create_all()
    
    # app.run(debug=True)
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, debug=True, port=port)
