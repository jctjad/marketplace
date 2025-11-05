from flask import Blueprint, render_template, redirect, url_for
from models import Item, User
#Auth Security
from flask_login import (  # current_user here to implement further security down the line
    current_user, login_required)

main_blueprint = Blueprint('main', __name__)
item_blueprint = Blueprint('item', __name__)
profile_blueprint = Blueprint('profile', __name__)

@main_blueprint.route('/')
@login_required
def goto_browse_items_page():
    return render_template('index.html')

@item_blueprint.route('/item/<int:item_id>')
@login_required
def goto_item_page(item_id):
    # Get item by ID (or 404 if not found)
    item = Item.query.get_or_404(item_id)
    
    # Get seller info (using the foreign key)
    seller = User.query.get(item.seller_id)
    
    return render_template('item.html', item=item, seller=seller)

@profile_blueprint.route('/profile')
@login_required
def goto_profile_page():
    return render_template('profile.html')
