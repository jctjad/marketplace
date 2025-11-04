from flask import Blueprint, render_template, redirect, url_for, request, flash
from models import Item, User, db
import os
from werkzeug.utils import secure_filename 

main_blueprint = Blueprint('main', __name__)
item_blueprint = Blueprint('item', __name__)
profile_blueprint = Blueprint('profile', __name__)

@main_blueprint.route('/')
def goto_browse_items_page():
    return render_template('index.html')

@item_blueprint.route('/item/<int:item_id>')
def goto_item_page(item_id):
    # Get item by ID (or 404 if not found)
    item = Item.query.get_or_404(item_id)
    
    # Get seller info (using the foreign key)
    seller = User.query.get(item.seller_id)
    
    return render_template('item.html', item=item, seller=seller)

HERE = os.path.abspath(os.path.dirname(__file__))             # ✅ this file's dir
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
        print("📥 image_file in request:", image_file)   # 👀 quick debug

        if image_file and image_file.filename and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            save_path = os.path.join(UPLOAD_FOLDER, filename)   # absolute save path
            image_file.save(save_path)
            image_path = f"/static/uploads/{filename}"          # URL path for template
            print("✅ saved to:", save_path)
        else:
            image_path = "/static/assets/item_placeholder.svg"
            print("⚠️ no valid upload; using placeholder")

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
            payment_options=payment_options,
            condition=condition
        )

        db.session.add(new_item)
        db.session.commit()
        flash('✅ Item created successfully!', 'success')
        return redirect(url_for('item.goto_item_page', item_id=new_item.id))

    return render_template('create_item.html')

@profile_blueprint.route('/profile')
def goto_profile_page():
    return render_template('profile.html')
