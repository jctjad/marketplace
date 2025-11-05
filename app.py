from flask import Flask
from views import main_blueprint, item_blueprint, profile_blueprint
from models import db, User

#Auth Libraries
from auth import auth_blueprint
from flask_login import LoginManager

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///todo.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_keyyyyy'
db.init_app(app)

#Auth Section
login_man = LoginManager(app)
login_man.login_view = 'auth.signup'

@login_man.user_loader
def load_user(id):
    return User.query.get(int(id))

#Blue Register Section
app.register_blueprint(main_blueprint)
app.register_blueprint(item_blueprint)
app.register_blueprint(profile_blueprint)
app.register_blueprint(auth_blueprint)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
