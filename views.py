from flask import Blueprint, render_template, redirect, url_for, request, flash
from models import Item, User, db

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

@item_blueprint.route('/item/new', methods=['GET', 'POST'])
def create_item():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        condition = request.form.get('condition')
        payment_options = request.form.getlist('payment_options')

        image_file = request.files.get('image_file')
        if image_file and image_file.filename != "":
            image_path = f"/static/uploads/{image_file.filename}"
            image_file.save(f"app{image_path}")  # adjust path if needed
        else:
            image_path = "/static/assets/item_placeholder.svg"

        seller = User.query.first()

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
