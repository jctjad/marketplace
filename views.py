from flask import Blueprint, redirect, render_template, url_for
#Auth Security
from flask_login import (  # current_user here to implement further security down the line
    current_user, login_required)
from models import db, User, Item, Chat
from flask import send_file
from datetime import datetime
import csv

main_blueprint = Blueprint('main', __name__)
item_blueprint = Blueprint('item', __name__)
profile_blueprint = Blueprint('profile', __name__)

@main_blueprint.route('/')
@login_required
def goto_browse_items_page():
    return render_template('index.html')

@item_blueprint.route('/item')
@login_required
def goto_item_page():
    return render_template('item.html')

@profile_blueprint.route('/profile')
@login_required
def goto_profile_page():
    return render_template('profile.html')

@main_blueprint.route('/export')
@login_required
def export():
    # generate_Fake_Data() # this is to test to see if the csv populates
    get_User_Data()
    get_Item_Data()
    get_Chat_Data()
    return redirect(url_for('main.goto_browse_items_page'))

@main_blueprint.route('/import')
@login_required
def populate():
    clear_data() # before populating the database, we want to make sure it is empty
    populate_User_Data()
    populate_Item_Data()
    populate_Chat_Data()
    return redirect(url_for('main.goto_browse_items_page'))

# this helper method clears the database but maintains the structure
# Method from vkotovv on GitHub
def clear_data():
    meta = db.metadata
    for table in reversed(meta.sorted_tables):
        print('Clear table %s', table)
        db.session.execute(table.delete())
    db.session.commit()

# this helper method gets the User data
def get_User_Data():
    users = db.session.query(User).all()
    with open('../marketplace/data/Users.csv', 'w', newline='') as csvfile:
        csvwrite = csv.writer(csvfile, delimiter=',')
        csvwrite.writerow(["User ID", "Email", "First Name", "Last Name", "Profile Image", "Profile Description", "Bookmarks", "Items Selling", "Date Created"])
        for user in users:
            csvwrite.writerow([user.id, user.email, user.first_name, user.last_name, user.profile_image,
                               user.profile_description, user.bookmark_items, user.selling_items, user.date_created])

# this helper method gets Item data
def get_Item_Data():
    items = db.session.query(Item).all()
    with open('../marketplace/data/Items.csv', 'w', newline='') as csvfile:
        csvwrite = csv.writer(csvfile, delimiter=',')
        csvwrite.writerow(["Item ID", "Seller ID", "Item Name", "Item Description", "Item Photos", "Price", "Payment Options", "Live On Market", "Date Created"])
        for item in items:
            csvwrite.writerow([item.id, item.seller_id, item.name, item.description, item.item_photos, item.price, 
                               item.payment_options, item.live_on_market, item.date_created])
            
# this helper method gets the Chat data
def get_Chat_Data():
    chats = db.session.query(Chat).all()
    with open('../marketplace/data/Chats.csv', 'w', newline='') as csvfile:
        csvwrite = csv.writer(csvfile, delimiter=',')
        csvwrite.writerow(["Chat ID", "Item ID", "Seller ID", "Buyer IDs", "Messages"])
        for chat in chats:
            csvwrite.writerow([chat.id, chat.item_id, chat.seller_id, chat.buyer_ids, chat.messages])

# this method will populate the db with some fake data
def generate_Fake_Data():
    new_user1 = User(email='gru@minion.com', first_name='Gru', last_name='Minion', date_created=datetime.today())
    new_user2 = User(email='ash@pokemon.com', first_name='Ash', last_name='Ketchum', date_created=datetime.today())
    new_user3 = User(email='john@mail.com', first_name='John', last_name='Frisbee', date_created=datetime.today())
    db.session.add(new_user1)
    db.session.add(new_user2)
    db.session.add(new_user3)
    db.session.commit()

    new_item1 = Item(seller_id=new_user1.id, name='banana', item_photos='null', price=3, date_created = datetime.today())
    new_item3 = Item(seller_id=new_user2.id, name='pokeball', item_photos='null', price=15, date_created = datetime.today())
    new_item2 = Item(seller_id=new_user1.id, name='ray gun', item_photos='null', price=300, date_created = datetime.today())
    new_item4 = Item(seller_id=new_user3.id, name='disc', item_photos='null', price=12, date_created = datetime.today())
    new_item5 = Item(seller_id=new_user3.id, name='cones', item_photos='null', price=5, date_created = datetime.today())
    db.session.add(new_item1)
    db.session.add(new_item2)
    db.session.add(new_item3)
    db.session.add(new_item4)
    db.session.add(new_item5)
    db.session.commit()

# this helper method populates the User database
def populate_User_Data():
    # going line by line, add the record to the db
    with open('../marketplace/data/Users.csv', 'r', newline='') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        next(csvreader) # skips the header line
        for row in csvreader:
            new_user = User(id=row[0], email=row[1], first_name=row[2], last_name=row[3], profile_image=row[4],
                            profile_description=row[5], bookmark_items=row[6], selling_items=row[7], date_created=datetime.fromisoformat(row[8]))
            db.session.add(new_user)
        db.session.commit()

# this helper method populates the Item database
def populate_Item_Data():
    # going line by line, add the record to the db
    with open('../marketplace/data/Items.csv', 'r', newline='') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        next(csvreader) # skips the header line
        for row in csvreader:
            new_item = Item(id=row[0], seller_id=row[1], name=row[2], description=row[3], item_photos=row[4], price=row[5],
                            payment_options=row[6], live_on_market=bool((row[7] == 'True')), date_created=datetime.fromisoformat(row[8]))
            db.session.add(new_item)
        db.session.commit()

# this helper method populates the Chat database
def populate_Chat_Data():
    # going line by line, add the record to the db
    with open('../marketplace/data/Chats.csv', 'r', newline='') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        next(csvreader) # skips the header line
        for row in csvreader:
            new_item = Chat(id=row[0], item_id=row[1], seller_id=row[2], buyer_ids=row[3], messages=row[4])
            db.session.add(new_item)
        db.session.commit()
