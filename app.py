import os
from flask import Flask
from views import main_blueprint, item_blueprint, profile_blueprint
from models import db, User

#Messaging import
from setup_socket import app, socketio

#Auth Libraries
from auth import auth_blueprint
from flask_login import LoginManager

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

db.init_app(app)

#Auth Section
login_man = LoginManager(app)
login_man.login_view = 'auth.signup'
login_man.login_message = None

@login_man.user_loader
def load_user(id):
    return User.query.get(int(id))

# socketio = SocketIO(app) # wrapping our app in SocektIO to enable WebSocket capabilities

#Blue Register Section
app.register_blueprint(main_blueprint)
app.register_blueprint(item_blueprint)
app.register_blueprint(profile_blueprint)
app.register_blueprint(auth_blueprint)

# auto create tables in local dev only
if uri.startswith("sqlite:///"):
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    # app.run(debug=True)
    socketio.run(app, debug=True)