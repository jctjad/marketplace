"""views.py"""

import os
import io # for our file
from datetime import datetime
from PIL import Image, UnidentifiedImageError
import cloudinary # to send our images to cloudinary
import cloudinary.uploader
from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, send_from_directory, jsonify
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from flask_socketio import emit, join_room, leave_room
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
    room_id = item_id
    join_room(room_id)
    emit("message", f"{user['first_name']} {user['last_name']} has joined the chat", room=room_id)


@socketio.on("message")
def handle_message(data, user):
    """
    This function handles when the user sends a message to the chat room.
    """
    emit("message", f"{user['first_name']} {user['last_name']}: {data}", broadcast=True)


@socketio.on("leave")
def handle_disconnect(item, user):
    """
    This function handles when the user leaves/disconenct from the chat/page.
    """
    # user = User.query.filter_by(id=current_user.id).first()
    item_id = item["id"]
    room_id = item_id
    emit("message", f"{user['first_name']} {user['last_name']} left the chat", broadcast=True)
    leave_room(room_id)


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
            except UnidentifiedImageError:
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
            except UnidentifiedImageError:
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
