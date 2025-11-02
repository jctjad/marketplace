from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.sqlite import JSON
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(80), unique=True, nullable=False)
    first_name = db.Column(db.String(40), nullable=False)
    last_name = db.Column(db.String(40), nullable=False)
    profile_image = db.Column(db.String(255))   # String: path to image (static/assets..)
    profile_description = db.Column(db.String(2000))
    bookmark_items = db.Column(db.JSON, default=list)   # List of item_ids bookmarked by user
    selling_items = db.Column(db.JSON, default=list)   # List of item_ids being sold by user
    date_created = db.Column(db.DateTime, nullable=False, default=datetime)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(2000))
    item_photos = db.Column(db.String(255), nullable=False)
    price = db.Column(db.float)
    payment_options = db.Column(db.JSON, default=list)  # List of payment options for transaction
    live_on_market = db.Column(db.boolean, nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime)




