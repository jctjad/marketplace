from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, current_app, send_file
)
from models import db, User, Item, Chat
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import csv
import imghdr
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from setup_socket import socketio # to access socketio

# --- Blueprints ---
main_blueprint = Blueprint('main', __name__)
item_blueprint = Blueprint('item', __name__)
profile_blueprint = Blueprint('profile', __name__)

# --- Paths & Upload Config (single source of truth) ---
HERE = os.path.abspath(os.path.dirname(__file__))                 # this file's dir
STATIC_DIR = os.path.join(HERE, "static")                         # .../marketplace/static
UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")               # .../static/uploads  (items)
AVATAR_FOLDER = os.path.join(UPLOAD_FOLDER, "avatars")            # .../static/uploads/avatars (avatars)
DATA_FOLDER = os.path.join(STATIC_DIR, "data")                    # .../static/data

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AVATAR_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

# Item image types (you previously allowed these)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Avatar (profile) strict mimetypes
AVATAR_ALLOWED_MIMES = {'image/png', 'image/jpeg'}

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =====================================================
# HTML ROUTES (NO JINJA DATA) – FRONTEND SHELL ONLY
# =====================================================

# =========================
# Main / Browse
# =========================
@main_blueprint.route('/')
@login_required
def goto_browse_items_page():
    """
    CHANGED: This now ONLY returns a static HTML template.
    The grid of items is fetched via the REST API in script.js.
    """
    return render_template("index.html")  # no 'items' passed in

# =========================
# Items
# =========================
@item_blueprint.route('/item/<int:item_id>')
@login_required
def goto_item_page(item_id):
    """
    CHANGED: We do NOT look up the item here anymore.
    We just return the same item.html shell for ANY id.
    script.js reads `window.location.pathname` to figure out the id,
    then fetches item details via GET /api/items/<id>.
    """
    return render_template("item.html")


@item_blueprint.route("/item/new", methods=["GET"])
@login_required
def create_item_page():
    """
    NEW: This route only serves the static create_item.html page.
    The actual creation is done by the REST API: POST /api/items
    called via fetch() in script.js.
    """
    return render_template("create_item.html")

@socketio.on('join')
def handle_join(item_id):
    join_room(item_id)
    emit("message", f"Buyer has joined the chat", room=item_id)
    
# Handle user messages
@socketio.on('message')
def handle_message(data):
    emit("message", f"{data}", broadcast=True)

# Handle disconnects
@socketio.on('disconnect')
def handle_disconnect():
    emit("message", f"Buyer left the chat", broadcast=True)


# =========================
# Profile (View + Edit)
# =========================
@profile_blueprint.route('/profile')
@login_required
def goto_profile_page():
    """
    Profile page is now a static shell as well.
    script.js calls GET /api/profile/me to fill in the data.
    """
    return render_template('profile.html')


@profile_blueprint.route('/profile/edit', methods=['GET'])
@login_required
def goto_edit_profile_page():
    """
    Edit profile page HTML is static.
    script.js calls GET /api/profile/me to pre-fill the form.
    On submit, we still do a normal form POST to this same URL.
    """
    return render_template('edit_profile.html')


@profile_blueprint.route("/profile/edit", methods=["POST"])
@login_required
def save_profile_edits():
    """
    CHANGED only slightly: same logic, but the templates no longer
    use Jinja – they are populated via JS from /api/profile/me.
    """
    # Update bio (public profile description)
    bio = (request.form.get("profile_description") or "").strip()[:2000]
    current_user.profile_description = bio

    # Optional avatar upload (strict PNG/JPEG)
    f = request.files.get("avatar")
    if f and f.filename:
        if f.mimetype not in AVATAR_ALLOWED_MIMES:
            flash("Avatar must be PNG or JPEG (≤ 5 MB).", "error")
            return redirect(url_for("profile.goto_edit_profile_page"))

        filename = secure_filename(f"{current_user.id}_{f.filename}")
        dest = os.path.join(AVATAR_FOLDER, filename)
        f.save(dest)

        # Magic-bytes sanity check
        kind = imghdr.what(dest)
        if kind not in ("png", "jpeg", "jpg"):
            os.remove(dest)
            flash("Invalid image file.", "error")
            return redirect(url_for("profile.goto_edit_profile_page"))

        # Build a /static/... URL for templates & REST API
        rel = os.path.relpath(dest, STATIC_DIR).replace("\\", "/")
        current_user.profile_image = f"/static/{rel}"

    db.session.commit()
    flash("Profile updated!", "success")
    return redirect(url_for("profile.goto_profile_page"))


# =========================
# Export / Import
# =========================
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
    clear_data()
    populate_User_Data()
    populate_Item_Data()
    populate_Chat_Data()
    # clear_uploads()  # optional: not implemented fully
    return redirect(url_for('main.goto_browse_items_page'))


# =========================
# Helpers: DB & Files
# =========================
def clear_data():
    meta = db.metadata
    for table in reversed(meta.sorted_tables):
        print('Cleared table', table.name)
        db.session.execute(table.delete())
    db.session.commit()


def clear_uploads():
    # Example stub: remove images in uploads not referenced by Items
    upload_path = UPLOAD_FOLDER
    try:
        item_paths = {i.item_photos.lstrip('/') for i in db.session.query(Item).all() if i.item_photos}
        for fname in os.listdir(upload_path):
            candidate_rel = f"static/uploads/{fname}"
            if candidate_rel not in item_paths:
                # os.remove(os.path.join(upload_path, fname))
                pass  # left as a no-op to avoid unintended deletes
    except Exception as e:
        print("clear_uploads skipped:", e)


def get_User_Data():
    users = db.session.query(User).all()
    with open(os.path.join(DATA_FOLDER, 'Users.csv'), 'w', newline='') as csvfile:
        csvwrite = csv.writer(csvfile, delimiter=',')
        csvwrite.writerow(["User ID", "Email", "Password Hash", "First Name", "Last Name", "Profile Image", "Profile Description", "Bookmarks", "Items Selling", "Date Created"])
        for user in users:
            csvwrite.writerow([user.id, user.email, user.password_hash, user.first_name, user.last_name, user.profile_image,
                               user.profile_description, user.bookmark_items, user.selling_items, user.date_created])

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


def generate_Fake_Data():
    new_user1 = User(email='gru@minion.com', first_name='Gru', last_name='Minion', date_created=datetime.today())
    new_user2 = User(email='ash@pokemon.com', first_name='Ash', last_name='Ketchum', date_created=datetime.today())
    new_user3 = User(email='john@mail.com', first_name='John', last_name='Frisbee', date_created=datetime.today())
    db.session.add_all([new_user1, new_user2, new_user3])
    db.session.commit()

    new_item1 = Item(seller_id=new_user1.id, name='banana', item_photos='banana.png', price=3, date_created=datetime.today())
    new_item2 = Item(seller_id=new_user1.id, name='ray gun', item_photos='raygun.png', price=300, date_created=datetime.today())
    new_item3 = Item(seller_id=new_user2.id, name='pokeball', item_photos='pokeball.png', price=15, date_created=datetime.today())
    new_item4 = Item(seller_id=new_user3.id, name='disc', item_photos='ultra_star_disc.png', price=12, date_created=datetime.today())
    new_item5 = Item(seller_id=new_user3.id, name='cones', item_photos='cones.png', price=5, date_created=datetime.today())
    db.session.add_all([new_item1, new_item2, new_item3, new_item4, new_item5])
    db.session.commit()


def populate_User_Data():
    try:
        with open(os.path.join(DATA_FOLDER, 'Users.csv'), 'r', newline='') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',')
            first_line = csvfile.readline()
            if not csv.Sniffer().has_header(first_line):
                csvfile.seek(0)
            for row in csvreader:
                new_user = User(id=row[0], email=row[1], password_hash=row[2], first_name=row[3], last_name=row[4], profile_image=row[5],
                                profile_description=row[6], bookmark_items=row[7], selling_items=row[8], date_created=datetime.fromisoformat(row[9]))
                db.session.add(new_user)
            db.session.commit()
    except Exception as e:
        print("Cannot import Users.csv:", e)


def populate_Item_Data():
    try:
        with open(os.path.join(DATA_FOLDER, 'Items.csv'), 'r', newline='') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',')
            first_line = csvfile.readline()
            if not csv.Sniffer().has_header(first_line):
                csvfile.seek(0)
            for row in csvreader:
                new_item = Item(id=row[0], seller_id=row[1], name=row[2], description=row[3], item_photos=row[4], price=row[5],
                                conditon=row[6], payment_options=row[7], live_on_market=bool((row[8] == 'True')), date_created=datetime.fromisoformat(row[9]))
                db.session.add(new_item)
            db.session.commit()
    except Exception as e:
        print("Cannot import Items.csv:", e)


def populate_Chat_Data():
    try:
        with open(os.path.join(DATA_FOLDER, 'Chats.csv'), 'r', newline='') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',')
            first_line = csvfile.readline()
            if not csv.Sniffer().has_header(first_line):
                csvfile.seek(0)
            for row in csvreader:
                new_item = Chat(
                    id=row[0], item_id=row[1], seller_id=row[2],
                    buyer_ids=row[3], messages=row[4]
                )
                db.session.add(new_item)
            db.session.commit()
    except Exception as e:
        print("Cannot import Chats.csv:", e)

# =====================================================
# REST API ROUTES – REAL “BACKEND”
# =====================================================

@main_blueprint.route("/api/items", methods=["GET"])
@login_required
def api_list_items():
    """
    NEW: REST endpoint for listing items.
    Optional ?q= search param to filter by name, description, condition.
    """
    q = (request.args.get("q") or "").strip().lower()

    query = Item.query.filter_by(live_on_market=True)

    if q:
        like = f"%{q}%"
        query = query.filter(
            (Item.name.ilike(like))
            | (Item.description.ilike(like))
            | (Item.condition.ilike(like))
        )

    items = query.order_by(Item.date_created.desc()).all()
    return {"items": [item.to_dict() for item in items]}


@main_blueprint.route("/api/items/<int:item_id>", methods=["GET"])
@login_required
def api_get_item(item_id):
    """
    NEW: REST endpoint for a single item, used by item.html via JS.
    """
    item = Item.query.get_or_404(item_id)
    return {"item": item.to_dict()}


@main_blueprint.route("/api/items", methods=["POST"])
@login_required
def api_create_item():
    """
    NEW: REST endpoint for creating an item.
    Accepts multipart form-data (image + fields) from create_item.html via fetch().
    """
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    price_raw = request.form.get("price")
    condition = request.form.get("condition", "").strip()
    payment_options = request.form.getlist("payment_options")

    if not name or not price_raw:
        return {"error": "Name and price are required."}, 400

    try:
        price = float(price_raw)
    except ValueError:
        return {"error": "Price must be a valid number."}, 400

    # Handle image upload
    image_file = request.files.get("image_file")
    if image_file and image_file.filename and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        image_file.save(save_path)
        image_path = f"/static/uploads/{filename}"
    else:
        image_path = "/static/assets/item_placeholder.svg"

    new_item = Item(
        seller_id=current_user.id,
        name=name,
        description=description,
        item_photos=image_path,
        price=price,
        condition=condition,
        payment_options=payment_options,
        live_on_market=True,
        date_created=datetime.today(),
    )

    db.session.add(new_item)
    db.session.commit()

    # Optional: update user's selling_items list
    selling = current_user.selling_items or []
    selling.append(new_item.id)
    current_user.selling_items = selling
    db.session.commit()

    return {"item": new_item.to_dict()}, 201


@profile_blueprint.route("/api/profile/me", methods=["GET"])
@login_required
def api_profile_me():
    """
    NEW: REST endpoint for current user's profile data.
    Used by profile.html and edit_profile.html via JS.
    """
    return {"user": current_user.to_dict()}