import os
import sys

# Add project root to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from website import create_app
from website.models import db



@pytest.fixture()
def test_client():
    #Setting the Testing Config environment prior to Flask App creation
    os.environ['CONFIG_TYPE'] = 'config.TestingConfig'
    flask_app = create_app()

    #Creating Test Client using Flask app configured for tests
    with flask_app.test_client() as test_client:
        yield test_client


@pytest.fixture(autouse=True) #Automatically runs for every test
def reset_database(app):
    with app.app_context(): #ensures db is associated with flask app
        #recreates database for everytest
        db.drop_all()
        db.create_all()
        yield
        #clears database after each test
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def app():
    flask_app = create_app()
    return flask_app
