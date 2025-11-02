from flask import Blueprint, render_template, redirect, url_for

#Auth Security
from flask_login import login_required, current_user #current_user here to implement further security down the line

main_blueprint = Blueprint('main', __name__)
item_blueprint = Blueprint('item', __name__)
profile_blueprint = Blueprint('profile', __name__)

@main_blueprint.route('/')
@login_required
def goto_browse_items_page():
    return render_template('index.html')

@item_blueprint.route('/item')
def goto_item_page():
    return render_template('item.html')

@profile_blueprint.route('/profile')
def goto_profile_page():
    return render_template('profile.html')
