from flask import Blueprint, render_template, redirect, url_for, request, flash
from models import db, User, Item, Chat
from flask import send_file, flash
from datetime import datetime
import csv
import os
from werkzeug.utils import secure_filename 
#Auth Security
from flask_login import (  # current_user here to implement further security down the line
    current_user, login_required)

main_blueprint = Blueprint('main', __name__)
item_blueprint = Blueprint('item', __name__)
profile_blueprint = Blueprint('profile', __name__)

HERE = os.path.abspath(os.path.dirname(__file__))             # this file's dir
STATIC_DIR = os.path.join(HERE, "static")                     # e.g. .../marketplace/static
UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")           # .../static/uploads
DATA_FOLDER = os.path.join(STATIC_DIR, "data")                # .../static/data
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


@main_blueprint.route('/')
@login_required
def goto_browse_items_page():
    # fetch all items from database
    items = Item.query.order_by(Item.date_created.desc()).all()
    return render_template('index.html', items=items)

@item_blueprint.route('/item/<int:item_id>')
@login_required
def goto_item_page(item_id):
    # Get item by ID (or 404 if not found)
    item = Item.query.get_or_404(item_id)
    
    # Get seller info (using the foreign key)
    seller = User.query.get(item.seller_id)
    
    return render_template('item.html', item=item, seller=seller)

HERE = os.path.abspath(os.path.dirname(__file__))             # this file's dir
STATIC_DIR = os.path.join(HERE, "static")                     # e.g. .../marketplace/static
UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")           # .../static/uploads
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@item_blueprint.route('/item/new', methods=['GET', 'POST'])
def create_item():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        condition = request.form.get('condition')
        payment_options = request.form.getlist('payment_options')

        image_file = request.files.get('image_file')
        print("image_file in request:", image_file)   # 👀 quick debug

        if image_file and image_file.filename and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            save_path = os.path.join(UPLOAD_FOLDER, filename)   # absolute save path
            image_file.save(save_path)
            image_path = f"/static/uploads/{filename}"          # URL path for template
            print("saved to:", save_path)
        else:
            image_path = "/static/assets/item_placeholder.svg"
            print("no valid upload; using placeholder")

        seller = User.query.first()
        if not seller:
            flash("Create a user first (no seller in DB).", "error")
            return redirect(url_for('main.goto_browse_items_page'))

        new_item = Item(
            seller_id=seller.id,
            name=name,
            description=description,
            item_photos=image_path,
            price=price,
            condition=condition,
            payment_options=payment_options,
            live_on_market=True,
            date_created=datetime.today()
        )

        db.session.add(new_item)
        db.session.commit()
        flash('Item created successfully!', 'success')
        return redirect(url_for('item.goto_item_page', item_id=new_item.id))

    return render_template('create_item.html')

@profile_blueprint.route('/profile')
@login_required
def goto_profile_page():
    return render_template('profile.html')

@main_blueprint.route('/export')
@login_required
def export():
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
    # generate_Fake_Data()  # Test data to see if the csv populates
     # clear_uploads()  # Removes images that are no longer in the db from the uploads folder (not implemented)
    return redirect(url_for('main.goto_browse_items_page'))

# Clears the database but maintains the structure
def clear_data():   # Method from vkotovv on GitHub
    meta = db.metadata
    for table in reversed(meta.sorted_tables):
        print('Cleared table')
        db.session.execute(table.delete())
    db.session.commit()

# Removes images from the upload folder if they aren't in User
def clear_uploads():
    path = os.getcwd()
    upload_path = 'static/uploads'
    for image in os.listdir(os.path.join(path, upload_path)):
        print(db.session.query(Item).filter(item_photos = image).all())

# Gets User data
def get_User_Data():
    users = db.session.query(User).all()
    with open(os.path.join(DATA_FOLDER, 'Users.csv'), 'w', newline='') as csvfile:
        csvwrite = csv.writer(csvfile, delimiter=',')
        csvwrite.writerow(["User ID", "Email", "Password Hash", "First Name", "Last Name", "Profile Image", "Profile Description", "Bookmarks", "Items Selling", "Date Created"])
        for user in users:
            csvwrite.writerow([user.id, user.email, user.password_hash, user.first_name, user.last_name, user.profile_image,
                               user.profile_description, user.bookmark_items, user.selling_items, user.date_created])

# Gets Item data
def get_Item_Data():
    items = db.session.query(Item).all()
    with open(os.path.join(DATA_FOLDER, 'Items.csv'), 'w', newline='') as csvfile:
        csvwrite = csv.writer(csvfile, delimiter=',')
        csvwrite.writerow(["Item ID", "Seller ID", "Item Name", "Item Description", "Item Photos", "Price", "Condition", "Payment Options", "Live On Market", "Date Created"])
        for item in items:
            csvwrite.writerow([item.id, item.seller_id, item.name, item.description, item.item_photos, item.price, 
                               item.condition, item.payment_options, item.live_on_market, item.date_created])
            
# Gets the Chat data
def get_Chat_Data():
    chats = db.session.query(Chat).all()
    with open(os.path.join(DATA_FOLDER, 'Chats.csv'), 'w', newline='') as csvfile:
        csvwrite = csv.writer(csvfile, delimiter=',')
        csvwrite.writerow(["Chat ID", "Item ID", "Seller ID", "Buyer IDs", "Messages"])
        for chat in chats:
            csvwrite.writerow([chat.id, chat.item_id, chat.seller_id, chat.buyer_ids, chat.messages])

# Populate db with test data (may not work with password hashing)
def generate_Fake_Data():
    new_user1 = User(email='gru@minion.com', first_name='Gru', last_name='Minion', date_created=datetime.today())
    new_user2 = User(email='ash@pokemon.com', first_name='Ash', last_name='Ketchum', date_created=datetime.today())
    new_user3 = User(email='john@mail.com', first_name='John', last_name='Frisbee', date_created=datetime.today())
    db.session.add(new_user1)
    db.session.add(new_user2)
    db.session.add(new_user3)
    db.session.commit()

    new_item1 = Item(seller_id=new_user1.id, name='banana', item_photos='banana.png', price=3, date_created = datetime.today())
    new_item3 = Item(seller_id=new_user2.id, name='pokeball', item_photos='pokeball.png', price=15, date_created = datetime.today())
    new_item2 = Item(seller_id=new_user1.id, name='ray gun', item_photos='raygun.png', price=300, date_created = datetime.today())
    new_item4 = Item(seller_id=new_user3.id, name='disc', item_photos='ultra_star_disc.png', price=12, date_created = datetime.today())
    new_item5 = Item(seller_id=new_user3.id, name='cones', item_photos='cones.png', price=5, date_created = datetime.today())
    db.session.add(new_item1)
    db.session.add(new_item2)
    db.session.add(new_item3)
    db.session.add(new_item4)
    db.session.add(new_item5)
    db.session.commit()

# Populates the User database
def populate_User_Data():
    try:
        with open(os.path.join(DATA_FOLDER, 'Users.csv'), 'r', newline='') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',')
            # need to check if it has a header line
            if not csv.Sniffer().has_header(csvfile.readline()):
                csvfile.seek(0) # if there is no header, start with the first line, else skip it
            for row in csvreader:
                new_user = User(id=row[0], email=row[1], password_hash=row[2], first_name=row[3], last_name=row[4], profile_image=row[5],
                                profile_description=row[6], bookmark_items=row[7], selling_items=row[8], date_created=datetime.fromisoformat(row[9]))
                db.session.add(new_user)
            db.session.commit()
    except:
        print("Cannot import file: Users.csv not found")

# Populates the Item database
def populate_Item_Data():
    try:
        with open(os.path.join(DATA_FOLDER, 'Items.csv'), 'r', newline='') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',')
            # need to check if it has a header line
            if not csv.Sniffer().has_header(csvfile.readline()):
                csvfile.seek(0) # if there is no header, start with the first line, else skip it
            for row in csvreader:
                new_item = Item(id=row[0], seller_id=row[1], name=row[2], description=row[3], item_photos=row[4], price=row[5],
                                conditon=row[6], payment_options=row[7], live_on_market=bool((row[8] == 'True')), date_created=datetime.fromisoformat(row[9]))
                db.session.add(new_item)
            db.session.commit()
    except:
        print("Cannot import file: Item.csv not found")

# Populates the Chat database
def populate_Chat_Data():
    try:
        path = os.getcwd()
        with open(os.path.join(DATA_FOLDER, 'Chats.csv'), 'r', newline='') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',')
            # need to check if it has a header line
            if not csv.Sniffer().has_header(csvfile.readline()):
                csvfile.seek(0) # if there is no header, start with the first line, else skip it
            for row in csvreader:
                new_item = Chat(id=row[0], item_id=row[1], seller_id=row[2], buyer_ids=row[3], messages=row[4])
                db.session.add(new_item)
            db.session.commit()
    except:
        print("Cannot import file: Chat.csv not found")
