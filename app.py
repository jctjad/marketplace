import os
from flask import Flask
from views import main_blueprint, item_blueprint, profile_blueprint
from models import db, User
from authlib.integrations.flask_client import OAuth

#Auth Libraries
from auth import auth_blueprint
from flask_login import LoginManager

app = Flask(__name__)

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

#Client for Google Clode
app.config["GOOGLE_CLIENT_ID"] = os.environ.get("GOOGLE_CLIENT_ID")
app.config["GOOGLE_SECRET_KEY"] = os.environ.get("GOOGLE_SECRET_KEY")

db.init_app(app)

#OAuth Section

#Defining OAuth client manager
oauth = OAuth(app)

#Registers Google as an Identity Provider / don't forget to set the client id and key in heroku
google = oauth.register( #So this is google working for us
    name = 'google',
    client_id=app.config["GOOGLE_CLIENT_ID"],
    client_secret=app.config["GOOGLE_SECRET_KEY"],
    server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs = {'scope': 'openid profile email'}
)

#Adding app.config to register google. Helps auth.py use google too
app.config["GOOGLE_CLIENT"] = google

print("CLIENT ID:", app.config["GOOGLE_CLIENT_ID"])


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
    
    app.run(debug=True)
