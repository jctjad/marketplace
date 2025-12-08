from website.models import User, Item, Chat

def test_set_password():
    """
    GIVEN
    WHEN
    THEN
    """
    user = User()
    user.set_password('password')
    assert user.password_hash is not None
    assert user.password_hash is not 'password'

def test_check_password():
    """
    GIVEN
    WHEN
    THEN
    """
    user = User()
    user.set_password('password')
    assert user.check_password('password')
    assert not user.check_password('wrongpassword')

def test_to_dict():
    """
    GIVEN
    WHEN
    THEN
    """
    user = User(id=1, email='test@mail.com', first_name='John', last_name='Smith')
    user.set_password('password')
    user_dict = user.to_dict()
    print(user_dict)
    assert user_dict['id'] == 1
    assert user_dict['email'] == 'test@mail.com'
    assert user_dict['first_name'] == 'John'
    assert user_dict['last_name'] == 'Smith'
    assert user_dict['profile_image'] is None
    assert user_dict['profile_description'] is None
    assert user_dict['bookmark_items'] is None
    assert user_dict['selling_items'] is None
    assert user_dict['date_created'] is None
