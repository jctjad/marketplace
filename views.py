from flask import Blueprint, render_template, redirect
from flask import request
from models import db

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/', methods=['GET', 'POST'])
def browse_items():
    return render_template('index.html')
