from website.models import User, Item, Chat

def test_user_set_password():
    """
    GIVEN
    WHEN
    THEN
    """
    user = User()
    user.set_password('password')
    assert user.password_hash is not None
    assert user.password_hash != 'password'

def test_user_check_password():
    """
    GIVEN
    WHEN
    THEN
    """
    user = User()
    user.set_password('password')
    assert user.check_password('password')
    assert not user.check_password('wrongpassword')

def test_user_to_dict():
    """
    GIVEN
    WHEN
    THEN
    """
    user = User(id=1, email='test@mail.com', first_name='John', last_name='Smith')
    user.set_password('password')
    user_dict = user.to_dict()
    assert user_dict['id'] == 1
    assert user_dict['email'] == 'test@mail.com'
    assert user_dict['first_name'] == 'John'
    assert user_dict['last_name'] == 'Smith'
    assert user_dict['profile_image'] is None
    assert user_dict['profile_description'] is None
    assert user_dict['bookmark_items'] is None
    assert user_dict['selling_items'] is None
    assert user_dict['date_created'] is None

def test_item_to_dict():
    """
    GIVEN
    WHEN
    THEN
    """
    item = Item(name='item', description='selling', price='5.10', condition='new')
    item_dict = item.to_dict()
    assert item_dict['id'] is None
    assert item_dict['seller_id'] is None
    assert item_dict['name'] == 'item'
    assert item_dict['description'] == 'selling'    
    assert item_dict['item_photos'] is None
    assert item_dict['price'] == '5.10'
    assert item_dict['condition'] == 'new'
    assert item_dict['payment_options'] == []
    assert item_dict['bookmarked'] == False
    assert item_dict['live_on_market'] is None
    assert item_dict['date_created'] is None

def test_item_user():
    """
    GIVEN
    WHEN
    THEN
    """
    user = User(email='user@mail.com')
    item = Item(name='random item', seller=user)
    assert item.seller == user
    assert item.seller_id == user.id