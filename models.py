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

    # NEW: Backref from Item.seller (set in Item model below)
    items = db.relationship("Item", back_populates="seller", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    # NEW: Simple dict representation for REST API
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "profile_image": self.profile_image,
            "profile_description": self.profile_description,
            "bookmark_items": self.bookmark_items,
            "selling_items": self.selling_items,
            "date_created": self.date_created.isoformat() if self.date_created else None,
        }

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(2000))
    item_photos = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    condition = db.Column(db.String(50))
    payment_options = db.Column(db.JSON, default=list)  # List of payment options for transaction
    #bookmarked = db.Column(db.Boolean, default=False)
    live_on_market = db.Column(db.Boolean, default=True, nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # NEW: define seller relationship so we can access item.seller
    seller = db.relationship("User", back_populates="items", lazy=True)

    # NEW: dict representation for REST API and current user id is added
    def to_dict(self, include_seller=True, bookmarked=False, current_user_id=None):
        data = {
            "id": self.id,
            "seller_id": self.seller_id,
            "name": self.name,
            "description": self.description,
            "item_photos": self.item_photos,
            "price": self.price,
            "condition": self.condition,
            "payment_options": self.payment_options or [],
            "bookmarked": bool(bookmarked),
            "live_on_market": self.live_on_market,
            "date_created": self.date_created.isoformat() if self.date_created else None,
        }

        if include_seller and self.seller:
            data["seller"] = {
                "id": self.seller.id,
                "first_name": self.seller.first_name,
                "last_name": self.seller.last_name,
            }

        # NEW: add dynamic ownership flag (NOT stored in DB)
        if current_user_id is not None:
            data["is_owner"] = (self.seller_id == current_user_id)

        return data

class Chat(db.Model):   # The seller and buyer can chat (message one another) ON ITEM PAGE about given item
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    buyer_ids = db.Column(db.JSON, default=list)  # List of user_ids who message the seller on item page
    
    # Messages node data: (1) Message (str), (2) id (user_id), (3) next (next node in list)
    messages = db.Column(db.JSON, nullable=False, default=lambda: {"head": None, "tail": None, "nodes": {}})

    # (We’re not using Chat in the REST API yet, so no to_dict here for now.)
