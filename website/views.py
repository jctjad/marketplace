import os
import io # for our file
import csv
from datetime import datetime
from PIL import Image
import cloudinary # to send our images to cloudinary
import cloudinary.uploader
from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, send_from_directory, jsonify
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from flask_socketio import emit, join_room
from website.extensions import db, socketio
from .models import User, Item, Chat

# --- Blueprints ---
main_blueprint = Blueprint('main', __name__)
item_blueprint = Blueprint('item', __name__)
profile_blueprint = Blueprint('profile', __name__)

# --- Paths & Upload Config (single source of truth) ---
HERE = os.path.abspath(os.path.dirname(__file__))  # this file's dir
STATIC_DIR = os.path.join(HERE, "static")          # .../marketplace/static
UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")    # .../static/uploads  (items)
AVATAR_FOLDER = os.path.join(UPLOAD_FOLDER, "avatars") # .../static/uploads/avatars (avatars)
DATA_FOLDER = os.path.join(STATIC_DIR, "data")         # .../static/data

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AVATAR_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

# Want to check if it is being run locally or on Heroku
uri = os.getenv("DATABASE_URL")
asset_folder = "marketplace"
if uri is None:
    asset_folder = "local_marketplace"

# Item image types (you previously allowed these)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Avatar (profile) strict mimetypes
AVATAR_ALLOWED_MIMES = {'image/png', 'image/jpeg'}


def allowed_file(filename: str) -> bool:
    """
    This function checks to see if the file type is allowed.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# =====================================================
# HTML ROUTES (NO JINJA DATA) – FRONTEND SHELL ONLY
# =====================================================

# =========================
# Favicon
# =========================
@main_blueprint.route('/favicon.ico')
def favicon():
    """
    This sends the location of the favicon to the fetch request.
    """
    return send_from_directory(
        'static/assets',
        'favicon.ico',
        mimetype='image/x-icon'
    )


# =========================
# Main / Browse
# =========================
@main_blueprint.route('/')
@login_required
def goto_browse_items_page():
    """
    This now ONLY returns a static HTML template.
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
    We do NOT look up the item here anymore.
    We just return the same item.html shell for ANY id.
    script.js reads the URL to figure out the id,
    then fetches item details via GET /api/items/<id>.
    """
    return render_template("item.html")


@item_blueprint.route("/item/new", methods=["GET"])
@login_required
def create_item_page():
    """
    This route only serves the static create_item.html page.
    The actual creation is done by the REST API: POST /api/items
    called via fetch() in script.js.
    """
    return render_template("create_item.html")


# Socket.IO chat handlers
@socketio.on("join")
def handle_join(item, user):
    """
    This function handles when the user joins the chat room.
    """
    item_id = item["id"]
    # user_id = user["id"]
    # seller_id = item["seller_id"]
    room_id = item_id
    join_room(room_id)
    emit("message", f"{user['first_name']} {user['last_name']} has joined the chat", room=room_id)


@socketio.on("message")
def handle_message(data, user):
    """
    This function handles when the user sends a message to the chat room.
    """
    emit("message", f"{user['first_name']} {user['last_name']}: {data}", broadcast=True)


@socketio.on("disconnect")
def handle_disconnect():
    """
    This function handles when the user leaves/disconenct from the page.
    """
    user = User.query.filter_by(id=current_user.id).first()
    emit("message", f" {user.first_name} {user.last_name} left the chat", broadcast=True)


@item_blueprint.route('/item/<int:item_id>/edit')
@login_required
def edit_item_page(item_id):
    """
    This function wiil edit page shell (JS will fetch item + save via /api/items/<id>)
    """
    return render_template('edit_item.html')


# =========================
# Profile (View + Edit)
# =========================
@profile_blueprint.route('/profile')
@login_required
def goto_profile_page():
    """
    Profile page is a static shell.
    script.js calls GET /api/profile/me or /api/profile/<id>
    to fill in the data.
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
    Same logic, but the templates no longer use Jinja –
    they are populated via JS from /api/profile/me.
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
        print(asset_folder)
        if asset_folder == "marketplace":
            # Read to memory so Pillow can validate the image
            img_bytes = f.read()
            img_file = io.BytesIO(img_bytes)

            # Validate using magic bytes
            try:
                with Image.open(img_file) as img:
                    if img.format not in ("PNG", "JPEG", "JPG"):
                        return {"error": "Invalid image format"}, 400
            except Exception:
                return {"error": "Invalid image file"}, 400

            # Reset pointer after Pillow read
            img_file.seek(0)

            # Upload to Cloudinary
            filename = secure_filename(f"{current_user.id}_{f.filename}")

            upload_result = cloudinary.uploader.upload(
                img_file,
                public_id=f"{filename}",
                unique_filename=True,
                overwrite=True,
                asset_folder=asset_folder+"_avatars"
            )

            image_path = upload_result.get("secure_url")
            current_user.profile_image = image_path

        else: # asset_folder == "local_marketplace"; we will save stuff locally if being run
            filename = secure_filename(f"{current_user.id}_{f.filename}")
            dest = os.path.join(AVATAR_FOLDER, filename)
            f.save(dest)

            # Magic-bytes sanity check
            try:
                with Image.open(dest) as img:
                    if img.format not in ("PNG", "JPEG", "JPG"):
                        os.remove(dest)
                        flash("Invalid image file.", "error")
                        return redirect(url_for("profile.goto_edit_profile_page"))
            except Exception:
                os.remove(dest)
                flash("Invalid image file.", "error")
                return redirect(url_for("profile.goto_edit_profile_page"))

            # Build a /static/... URL for templates & REST API
            rel = os.path.relpath(dest, STATIC_DIR).replace("\\", "/")
            current_user.profile_image = f"/static/{rel}"

    db.session.commit()
    flash("Profile updated!", "success")
    return redirect(url_for("profile.goto_profile_page"))


@profile_blueprint.route("/api/profile/me", methods=["GET"])
@login_required
def api_profile_me():
    """
    REST endpoint for current user's profile data.
    Used by profile.html and edit_profile.html via JS.
    """
    return {"user": current_user.to_dict()}


# NEW: public view of any user's profile
@profile_blueprint.route("/profile/<int:user_id>")
@login_required
def goto_public_profile(user_id):
    """
    Public view of another user's profile.
    Uses the same profile.html shell; script.js decides
    which user to load based on the URL.
    """
    return render_template("profile.html")


# NEW: REST for a specific user's public profile
@profile_blueprint.route("/api/profile/<int:user_id>", methods=["GET"])
@login_required
def api_profile_user(user_id):
    """
    REST endpoint for a specific user's public profile.
    Used when viewing seller profiles from an item page.
    """
    user = User.query.get_or_404(user_id)
    return {"user": user.to_dict()}


# =========================
# Export / Import
# =========================
@main_blueprint.route('/export')
@login_required
def export():
    """
    This function exports the database to a .csv.
    Currently this function does not work.
    """
    get_user_data()
    get_item_data()
    get_chat_data()
    return redirect(url_for('main.goto_browse_items_page'))


@main_blueprint.route('/import')
@login_required
def populate():
    """
    This function imports the database from a .csv to the current db.
    """
    clear_data()
    get_user_data()
    get_item_data()
    get_chat_data()
    return redirect(url_for('main.goto_browse_items_page'))


# =========================
# Helpers: DB & Files
# =========================
def clear_data():
    """
    This helper function helps clear the data currently in the db.
    """
    meta = db.metadata
    for table in reversed(meta.sorted_tables):
        print('Cleared table', table.name)
        db.session.execute(table.delete())
    db.session.commit()


def clear_uploads():
    """
    This helper function helps removes the images from uploads not referenced by Items.
    """
    # Example stub: remove images in uploads not referenced by Items
    upload_path = UPLOAD_FOLDER
    try:
        item_paths = {
            i.item_photos.lstrip('/')
            for i in db.session.query(Item).all()
            if i.item_photos
        }
        for fname in os.listdir(upload_path):
            candidate_rel = f"static/uploads/{fname}"
            if candidate_rel not in item_paths:
                # os.remove(os.path.join(upload_path, fname))
                pass  # no-op to avoid unintended deletes
    except Exception as e:
        print("clear_uploads skipped:", e)


def get_user_data():
    """
    This helper function helps get all the User data in the db and writes it to a .csv.
    """
    users = db.session.query(User).all()
    with open(os.path.join(DATA_FOLDER, 'Users.csv'), 'w', newline='') as csvfile:
        csvwrite = csv.writer(csvfile, delimiter=',')
        csvwrite.writerow([
            "User ID", "Email", "Password Hash", "First Name", "Last Name",
            "Profile Image", "Profile Description", "Bookmarks",
            "Items Selling", "Date Created"
        ])
        for user in users:
            csvwrite.writerow([
                user.id, user.email, user.password_hash, user.first_name,
                user.last_name, user.profile_image, user.profile_description,
                user.bookmark_items, user.selling_items, user.date_created
            ])


def get_item_data():
    """
    This helper function helps get all the Item data in the db and writes it to a .csv.
    """
    items = db.session.query(Item).all()
    with open(os.path.join(DATA_FOLDER, 'Items.csv'), 'w', newline='') as csvfile:
        csvwrite = csv.writer(csvfile, delimiter=',')
        csvwrite.writerow([
            "Item ID", "Seller ID", "Item Name", "Item Description",
            "Item Photos", "Price", "Condition", "Payment Options",
            "Live On Market", "Date Created"
        ])
        for item in items:
            csvwrite.writerow([
                item.id, item.seller_id, item.name, item.description,
                item.item_photos, item.price, item.condition,
                item.payment_options, item.live_on_market, item.date_created
            ])


def get_chat_data():
    """
    This helper function helps get all the Chat data in the db and writes it to a .csv.
    """
    chats = db.session.query(Chat).all()
    with open(os.path.join(DATA_FOLDER, 'Chats.csv'), 'w', newline='') as csvfile:
        csvwrite = csv.writer(csvfile, delimiter=',')
        csvwrite.writerow(["Chat ID", "Item ID", "Seller ID", "Buyer IDs", "Messages"])
        for chat in chats:
            csvwrite.writerow([
                chat.id, chat.item_id, chat.seller_id,
                chat.buyer_ids, chat.messages
            ])


def generate_fake_data():
    """
    This helper function helps set up a fake database for testing.
    Currently, this function is useless.
    """
    new_user1 = User(email='gru@minion.com', first_name='Gru',
                     last_name='Minion', date_created=datetime.today())
    new_user2 = User(email='ash@pokemon.com', first_name='Ash',
                     last_name='Ketchum', date_created=datetime.today())
    new_user3 = User(email='john@mail.com', first_name='John',
                     last_name='Frisbee', date_created=datetime.today())
    db.session.add_all([new_user1, new_user2, new_user3])
    db.session.commit()

    new_item1 = Item(seller_id=new_user1.id, name='banana',
                     item_photos='banana.png', price=3,
                     date_created=datetime.today())
    new_item2 = Item(seller_id=new_user1.id, name='ray gun',
                     item_photos='raygun.png', price=300,
                     date_created=datetime.today())
    new_item3 = Item(seller_id=new_user2.id, name='pokeball',
                     item_photos='pokeball.png', price=15,
                     date_created=datetime.today())
    new_item4 = Item(seller_id=new_user3.id, name='disc',
                     item_photos='ultra_star_disc.png', price=12,
                     date_created=datetime.today())
    new_item5 = Item(seller_id=new_user3.id, name='cones',
                     item_photos='cones.png', price=5,
                     date_created=datetime.today())
    db.session.add_all([new_item1, new_item2, new_item3, new_item4, new_item5])
    db.session.commit()


def populate_user_data():
    """
    This helper function helps read in the User data from a .csv.
    """
    try:
        with open(os.path.join(DATA_FOLDER, 'Users.csv'), 'r', newline='') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',')
            first_line = csvfile.readline()
            if not csv.Sniffer().has_header(first_line):
                csvfile.seek(0)
            for row in csvreader:
                new_user = User(
                    id=row[0], email=row[1], password_hash=row[2],
                    first_name=row[3], last_name=row[4], profile_image=row[5],
                    profile_description=row[6], bookmark_items=row[7],
                    selling_items=row[8],
                    date_created=datetime.fromisoformat(row[9])
                )
                db.session.add(new_user)
            db.session.commit()
    except Exception as e:
        print("Cannot import Users.csv:", e)


def populate_item_data():
    """
    This helper function helps read in the Item data from a .csv.
    """
    try:
        with open(os.path.join(DATA_FOLDER, 'Items.csv'), 'r', newline='') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',')
            first_line = csvfile.readline()
            if not csv.Sniffer().has_header(first_line):
                csvfile.seek(0)
            for row in csvreader:
                new_item = Item(
                    id=row[0], seller_id=row[1], name=row[2],
                    description=row[3], item_photos=row[4], price=row[5],
                    conditon=row[6], payment_options=row[7],
                    live_on_market=bool((row[8] == 'True')),
                    date_created=datetime.fromisoformat(row[9])
                )
                db.session.add(new_item)
            db.session.commit()
    except Exception as e:
        print("Cannot import Items.csv:", e)


def populate_chat_data():
    """
    This helper function helps read in the Chat data from a .csv.
    """
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

# =========================
# REST API: Items
# =========================
@item_blueprint.route("/api/items", methods=["GET"])
@login_required
def api_list_items():
    """
    REST endpoint for listing items.

    Optional query params:
      ?q=          full-text search on name/description/condition
      ?seller_id=  only items from a particular seller
    """
    q = (request.args.get("q") or "").strip().lower()
    seller_id = request.args.get("seller_id", type=int)

    query = Item.query

    if seller_id is not None:
        query = query.filter_by(seller_id=seller_id)

    if q:
        like = f"%{q}%"
        query = query.filter(
            Item.name.ilike(like) |
            Item.description.ilike(like) |
            Item.condition.ilike(like)
        )

    items = query.order_by(Item.date_created.desc()).all()
    bookmarked_ids = set(current_user.bookmark_items or [])  # Sets bookmark value

    return {
        "items": [
            item.to_dict(
                include_seller=True,
                bookmarked=(item.id in bookmarked_ids),
                current_user_id=current_user.id
            )
            for item in items
        ]
    }


@main_blueprint.route("/api/items/<int:item_id>", methods=["GET"], endpoint="api_get_item_v2")
@login_required
def api_get_item_v2(item_id):
    """
    REST endpoint for a single item, used by item.html via JS.
    """
    item = Item.query.get_or_404(item_id)
    bookmarked_ids = set(current_user.bookmark_items or [])
    return {
        "item": item.to_dict(
            include_seller=True,
            bookmarked=(item.id in bookmarked_ids),
            current_user_id=current_user.id
        )
    }


@item_blueprint.route("/api/items", methods=["POST"])
@login_required
def api_create_item():
    """
    REST endpoint for when creating an item.
    """
    # Accept multipart/form-data
    name = request.form.get("name")
    description = request.form.get("description")
    price = request.form.get("price")
    condition = request.form.get("condition")
    payment_options = request.form.getlist("payment_options")

    if not name or price is None or price == "":
        return {"error": "Missing name or price"}, 400

    # Validate price
    try:
        price_val = float(price)
    except (TypeError, ValueError):
        return {"error": "Price must be a number"}, 400

    if price_val < 0:
        return {"error": "Price cannot be negative"}, 400

    # handle file upload
    image_file = request.files.get("image_file")
    if image_file and image_file.filename:
        if asset_folder == "marketplace":
            # Read to memory so Pillow can validate the image
            img_bytes = image_file.read()
            img_file = io.BytesIO(img_bytes)

            # Validate using magic bytes
            try:
                with Image.open(img_file) as img:
                    if img.format not in ("PNG", "JPEG", "JPG"):
                        return {"error": "Invalid image format"}, 400
            except Exception:
                return {"error": "Invalid image file"}, 400

            # Reset pointer after Pillow read
            img_file.seek(0)

            # Upload to Cloudinary
            filename = secure_filename(f"{current_user.id}_{image_file.filename}")

            upload_result = cloudinary.uploader.upload(
                img_file,
                public_id=f"{filename}",
                unique_filename=True,
                overwrite=True,
                asset_folder=asset_folder+"_uploads"
            )

            image_path = upload_result.get("secure_url")

        else: # asset_folder == "local_marketplace"; we will save stuff locally if being run
            filename = secure_filename(f"{current_user.id}_{image_file.filename}")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            image_file.save(filepath)
            image_path = f"/static/uploads/{filename}"
    else:
        image_path = "/static/assets/item_placeholder.svg"

    new_item = Item(
        seller_id=current_user.id,
        name=name,
        description=description,
        price=price_val,
        condition=condition,
        payment_options=payment_options,
        item_photos=image_path
    )


    db.session.add(new_item)
    db.session.commit()

    selling = current_user.selling_items or []
    selling.append(new_item.id)
    current_user.selling_items = selling

    return {"item": new_item.to_dict(current_user_id=current_user.id)}, 201


@main_blueprint.route('/api/items/<int:item_id>', methods=['GET'])
@login_required
def api_get_item(item_id):
    """Get a single item by id."""
    item = Item.query.get_or_404(item_id)
    return {"item": item.to_dict(current_user_id=current_user.id)}


@main_blueprint.route('/api/items/<int:item_id>', methods=['PUT', 'PATCH'])
@login_required
def api_update_item(item_id):
    """Update an item you own."""
    item = Item.query.get_or_404(item_id)

    if item.seller_id != current_user.id:
        return {"error": "You can only edit your own items."}, 403

    request.content_type.startswith("multipart/form-data")
    name = request.form.get("name")
    description = request.form.get("description")
    price = request.form.get("price")
    condition = request.form.get("condition")
    payment_options = request.form.getlist("payment_options")

    # --- Optional image upload ---
    f = request.files.get("image_file")
    if f and f.filename:
        image_file = f

        if asset_folder == "marketplace":
            # Read to memory so Pillow can validate the image
            img_bytes = image_file.read()
            img_file = io.BytesIO(img_bytes)

            # Validate using magic bytes
            try:
                with Image.open(img_file) as img:
                    if img.format not in ("PNG", "JPEG", "JPG"):
                        return {"error": "Invalid image format"}, 400
            except Exception:
                return {"error": "Invalid image file"}, 400

            # Reset pointer after Pillow read
            img_file.seek(0)

            # Upload to Cloudinary
            filename = secure_filename(f"{current_user.id}_{image_file.filename}")

            upload_result = cloudinary.uploader.upload(
                img_file,
                public_id=f"{filename}",
                unique_filename=True,
                overwrite=True,
                asset_folder=asset_folder + "_uploads"
            )

            image_path = upload_result.get("secure_url")

        else:  # asset_folder == "local_marketplace"; save locally
            filename = secure_filename(f"{current_user.id}_{image_file.filename}")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            image_file.save(filepath)
            image_path = f"/static/uploads/{filename}"

        # Only update item_photos if a new image was actually uploaded
        item.item_photos = image_path

    # --- Always update these fields ---
    item.name = name
    item.description = description

    # (plus your price validation block we added earlier)
    if price is not None and price != "":
        try:
            price_val = float(price)
        except (TypeError, ValueError):
            return {"error": "Price must be a number"}, 400

        if price_val < 0:
            return {"error": "Price cannot be negative"}, 400

        item.price = price_val

    item.condition = condition
    item.payment_options = payment_options

    # data = request.get_json() or {}

    # if 'name' in data:
    #     item.name = (data['name'] or '').strip()
    # if 'description' in data:
    #     item.description = (data['description'] or '').strip()
    # if 'item_photos' in data:
    #     print("updating item's photos")
    #     print(data['item_photos'])
    #     item.item_photos = data['item_photos']
    # if 'price' in data:
    #     try:
    #         item.price = float(data['price'])
    #     except (TypeError, ValueError):
    #         return {"error": "Price must be a number"}, 400
    # if 'condition' in data:
    #     item.condition = data['condition']
    # if 'payment_options' in data:
    #     item.payment_options = data['payment_options'] or []

    db.session.commit()
    return {"item": item.to_dict(current_user_id=current_user.id)}


@main_blueprint.route('/api/items/<int:item_id>', methods=['DELETE'])
@login_required
def api_delete_item(item_id):
    """Hard delete an item you own."""
    item = Item.query.get_or_404(item_id)

    if item.seller_id != current_user.id:
        return {"error": "You can only delete your own items."}, 403

    db.session.delete(item)
    db.session.commit()
    return {"status": "deleted", "id": item_id}


@main_blueprint.route("/api/bookmark", methods=["POST"])
@login_required
def api_bookmark():
    """
    REST endpoint for bookmarked items.
    Used by index.html to store user bookmarks and sort via JS.
    """
    data = request.get_json(silent=True) or {}

    item_id = data.get("item_id")
    bookmarked = data.get("bookmarked")

    if item_id is None or bookmarked is None:
        return jsonify({"error": "Invalid payload"}), 400

    # Ensure item exists
    try:
        item_id = int(item_id)
    except (TypeError, ValueError):
        return jsonify({"error": "item_id must be an integer"}), 400
    item = Item.query.get(item_id)
    if item is None:
        return jsonify({"error": "Item not found"}), 404

    # Normalize bookmark list
    bookmarks = current_user.bookmark_items or []
    try:
        bookmarks = [int(b) for b in bookmarks]
    except (TypeError, ValueError):
        bookmarks = []

    # Toggle bookmark
    if bool(bookmarked):
        if item_id not in bookmarks:
            bookmarks.append(item_id)
    else:
        bookmarks = [b for b in bookmarks if b != item_id]

    current_user.bookmark_items = bookmarks
    db.session.commit()

    return jsonify({
        "status": "ok",
        "bookmarked": bool(bookmarked),
        "bookmarks": bookmarks,
    }), 200


# @item_blueprint.route("/api/messages/<string:room_id>", methods=["GET"])
# @login_required
# def api_get_messages(room_id):
#     return


@item_blueprint.route("/api/messages", methods=["POST"])
@login_required
def api_add_message():
    """
    REST endpoint for messaging.
    Currently, not functional.
    """
    user_data = request.form.get("user_data")

    item_data = request.form.get("item_data")
    msg_data = request.form.get("message")

    # NOTE: This block is incomplete and will need adjustment
    # if you actually want to persist chat messages.
    user_id = user_data['id']
    item_id = item_data['id']
    seller_id = item_data['seller_id']

    find_chat = Chat.query.filter_by(
        item_id=item_id, seller_id=seller_id, buyers_id=[user_id]
    ).first()
    if not find_chat:
        new_message = Chat(
            item_id=item_id,
            seller_id=seller_id,
            buyer_ids=[seller_id]
        )
        new_message.messages['head'] = new_message.id
        new_message.messages['nodes'] = {
            "msg_data": msg_data,
            "id": user_id,
            "next": None
        }
    # return
