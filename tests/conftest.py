import pytest
import os
from website import create_app, db, socketio
from website.models import User, Item

@pytest.fixture(scope='module')
def test_client():
    """
    """
    # Set the Testing configuration prior to creating the Flask application
    os.environ['CONFIG_TYPE'] = 'config.TestingConfig'
    flask_app = create_app()

    # Create a test client using the Flask application configured for testing
    with flask_app.test_client() as test_client:
        yield test_client # this is where the testing happens!


@pytest.fixture(scope='module')
def test_socketio_client():
    """
    """
    os.environ['CONFIG_TYPE'] = 'config.TestingConfig'
    app = create_app()
    test_client = app.test_client()
    socketio_test_client = socketio.test_client(app, flask_test_client=test_client)

    yield socketio_test_client

    socketio_test_client.disconnect()

@pytest.fixture(scope='module')
def test_data_socketio(test_client):
    """
    """
    with test_client.application.app_context():
        db.drop_all()
        db.create_all()

        user1 = User(email='test1@colby.edu', first_name='John', last_name='Smith')
        user1.set_password('password1')
        db.session.add(user1)

        user2 = User(email='test2@colby.edu', first_name='Sara', last_name='Taylor')
        user2.set_password('password2')
        db.session.add(user2)

        db.session.commit()

        item = Item(seller_id=user1.id, name='test_item', description='description for test item',
                    item_photos='placeholder.svg', price=10.0)
        
        db.session.add(item)
        db.session.commit()

        yield {'user1': user1, 'user2': user2, 'item': item}

        db.session.remove()
        db.drop_all()
