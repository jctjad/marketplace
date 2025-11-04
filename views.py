from flask import Blueprint, render_template, redirect, url_for
from models import db, User, Item, Chat
from flask import send_file
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
def get_User_Item():
    items = db.session.query(Item).join(User, User.id == Item.seller_id)
    with open('users_items.csv', 'w', newline='') as csvfile:
        csvwrite = csv.writer(csvfile, delimiter=',')
        for i in items:
            csvwrite.writerow([i.user.id, i.user.email, i.user.firstname, i.user.last_name, i.user.profile_image,
                               i.user.profile_description, i.user.bookmar_items, i.user.selling_items, i.user.data_create])
    return redirect(url_for('main.goto_browse_items_page'))