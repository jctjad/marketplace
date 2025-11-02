from flask import Blueprint, render_template, redirect, url_for
from models import Item, User

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

@profile_blueprint.route('/profile')
def goto_profile_page():
    return render_template('profile.html')
