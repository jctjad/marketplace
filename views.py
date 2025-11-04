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
def get_User_Item_Data():
    test_User_Item_Data() # this populates the db with fake data, for testing purposes

    # with db.session.no_autoflush:
    items = db.session.query(Item).join(User, User.id == Item.seller_id).all()
    with open('users_items.csv', 'w', newline='') as csvfile:
        csvwrite = csv.writer(csvfile, delimiter=',')
        for i in items:
            csvwrite.writerow([i.user.id, i.user.email, i.user.firstname, i.user.last_name, i.user.profile_image,
                               i.user.profile_description, i.user.bookmark_items, i.user.selling_items, i.user.data_create])
    return redirect(url_for('main.goto_browse_items_page'))

def test_User_Item_Data():
    # this method will populate the db with some fake data
    new_user1 = User(email='gru@minion.com', first_name='Gru', last_name='Minion', date_created=datetime.today())
    new_user2 = User(email='ash@pokemon.com', first_name='Ash', last_name='Ketchum', date_created=datetime.today())
    new_user3 = User(email='john@mail.com', first_name='John', last_name='Frisbee', date_created=datetime.today())
    db.session.add(new_user1)
    db.session.add(new_user2)
    db.session.add(new_user3)

    for i in range(2):
        new_item1 = Item(seller_id=new_user1.id, name='banana', item_photos='null', price=3, date_created = datetime.today())
        new_item2 = Item(seller_id=new_user2.id, name='pokeball', item_photos='null', price=5, date_created = datetime.today())
        new_item3 = Item(seller_id=new_user3.id, name='disc', item_photos='null', price=12, date_created = datetime.today())
        db.session.add(new_item1)
        db.session.add(new_item2)
        db.session.add(new_item3)

    # new_task = Task(title=task, user_id=current_user.id)
    # db.session.add(new_task)
    db.session.commit()