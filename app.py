from flask import Flask
from views import main_blueprint, item_blueprint, profile_blueprint
from models import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_keyyyyy'
db.init_app(app)

app.register_blueprint(main_blueprint)
app.register_blueprint(item_blueprint)
app.register_blueprint(profile_blueprint)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
