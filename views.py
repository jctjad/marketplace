from flask import Blueprint, render_template, redirect, url_for
from models import db, User, Item, Chat
from flask import send_file
from datetime import datetime
import csv

main_blueprint = Blueprint('main', __name__)
item_blueprint = Blueprint('item', __name__)
profile_blueprint = Blueprint('profile', __name__)

@main_blueprint.route('/')
def goto_browse_items_page():
    return render_template('index.html')

@item_blueprint.route('/item')
def goto_item_page():
    return render_template('item.html')

@profile_blueprint.route('/profile')
def goto_profile_page():
    return render_template('profile.html')

@main_blueprint.route('/export')
def export():
    get_User_Data()
    get_Item_Data()
    get_Chat_Data()
    return redirect(url_for('main.goto_browse_items_page'))

# this helper method gets the User data
def get_User_Data():
    users = db.session.query(User).all()
    with open('Users.csv', 'w', newline='') as csvfile:
        csvwrite = csv.writer(csvfile, delimiter=',')
        csvwrite.writerow(["User ID", "Email", "First Name", "Last Name", "Profile Image", "Profile Description", "Bookmarks", "Items Selling", "Date Created"])
        for user in users:
            csvwrite.writerow([user.id, user.email, user.first_name, user.last_name, user.profile_image,
                               user.profile_description, user.bookmark_items, user.selling_items, user.date_created])

# this helper method gets Item data
def get_Item_Data():
    items = db.session.query(Item).all()
    with open('Items.csv', 'w', newline='') as csvfile:
        csvwrite = csv.writer(csvfile, delimiter=',')
        csvwrite.writerow(["Item ID", "Seller ID", "Item Name", "Item Description", "Item Photos", "Price", "Payment Options", "Live On Market", "Date Created"])
        for item in items:
            csvwrite.writerow([item.id, item.seller_id, item.name, item.description, item.item_photos, item.price, 
                               item.payment_options, item.live_on_market, item.date_created])
            
# this helper method gets the Chat data
def get_Chat_Data():
    chats = db.session.query(Chat).all()
    with open('Chats.csv', 'w', newline='') as csvfile:
        csvwrite = csv.writer(csvfile, delimiter=',')
        csvwrite.writerow(["Chat ID", "Item ID", "Seller ID", "Buyer IDs", "Messages"])
        for chat in chats:
            csvwrite.writerow([chat.id, chat.item_id, chat.seller_id, chat.buyer_ids, chat.messages])