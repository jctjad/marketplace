from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.sqlite import JSON
from datetime import datetime

#Password Libraries
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin): #Added UserMixin parameter
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(80), unique=True, nullable=False) #Acts like username
    password_hash = db.Column(db.String(255), nullable=False) #Login Variable
    first_name = db.Column(db.String(40), nullable=False)
    last_name = db.Column(db.String(40), nullable=False)
    profile_image = db.Column(db.String(255))   # String: path to image (static/assets..)
    profile_description = db.Column(db.String(2000))
    bookmark_items = db.Column(db.JSON, default=list)   # List of item_ids bookmarked by user
    selling_items = db.Column(db.JSON, default=list)   # List of item_ids being sold by user
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(2000))
    item_photos = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    condition = db.Column(db.String(50))
    payment_options = db.Column(db.JSON, default=list)  # List of payment options for transaction
    live_on_market = db.Column(db.Boolean, default=True, nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Chat(db.Model):   # The seller and buyer can chat (message one another) ON ITEM PAGE about given item
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    buyer_ids = db.Column(db.JSON, default=list)  # List of user_ids who message the seller on item page
    
    # Messages node data: (1) Message (str), (2) id (user_id), (3) next (next node in list)
    messages = db.Column(db.JSON, nullable=False, default=lambda: {"head": None, "tail": None, "nodes": {}})


