"""test_views.py"""

import json
from website import db
from website.models import User, Item


def test_join(test_socketio_client, test_data_socketio):
    """
    GIVEN a user on the item page
    WHEN the user opens the chat popup
    THEN the user joins the chat with the appropriate message and
    is in the correct room
    """
    socketio = test_socketio_client['socketio']
    socketio_test_client = test_socketio_client['socketio_test_client']

    user1 = test_data_socketio['user1']
    item = test_data_socketio['item']

    socketio_test_client.emit("join", item.to_dict(), user1.to_dict())

    received = socketio_test_client.get_received()

    assert len(received) > 0

    room_state = socketio.server.manager.rooms.get('/', {})
    all_sids = list(room_state.values())  # list of dicts
    user1_sid = list(all_sids[0].keys())[0]

    # Checking to see that the room was created
    assert item.id in room_state
    # Checking to see that user1 joined the room
    assert user1_sid in room_state[item.id]

    event=received[0]
    assert event["name"] == "message"
    assert event["args"] == "John Smith has joined the chat"


def test_message(test_socketio_client, test_data_socketio):
    """
    GIVEN a user in a chat room
    WHEN the user sends a message
    THEN the message is received by the server
    """
    socketio_test_client = test_socketio_client['socketio_test_client']
    user1 = test_data_socketio['user1']
    item = test_data_socketio['item']

    socketio_test_client.emit("join", item.to_dict(), user1.to_dict())
    socketio_test_client.emit("message", "Hello there!", user1.to_dict())

    received = socketio_test_client.get_received()
    assert len(received) > 0

    event = received[1]
    assert event["name"] == "message"
    assert event["args"] == "John Smith: Hello there!"


def test_disconnect(test_socketio_client, test_data_socketio):
    """
    GIVEN a user is in a chat room
    WHEN the user closes the chat popup
    THEN the message of the user is sent and no longer in the room
    """
    socketio_test_client = test_socketio_client['socketio_test_client']
    user1 = test_data_socketio['user1']
    item = test_data_socketio['item']

    socketio_test_client.emit("join", item.to_dict(), user1.to_dict())
    socketio_test_client.emit("message", "Hello there!", user1.to_dict())
    socketio_test_client.emit("leave", item.to_dict(), user1.to_dict())

    received = socketio_test_client.get_received()
    assert len(received) > 0

    event = received[2]
    assert event["name"] == "message"
    assert event["args"] == "John Smith left the chat"

########################################
#     BASIC HTML PAGE SHELL ROUTES     #
########################################

def test_favicon_route(test_client):
    resp = test_client.get("/favicon.ico")
    assert resp.status_code == 200
    assert resp.mimetype == "image/x-icon"


def test_browse_items_page_renders(authed_client):
    client, _ = authed_client
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"<html" in resp.data.lower()


def test_item_shell_routes(authed_client):
    client, _ = authed_client

    resp_item = client.get("/item/123")
    assert resp_item.status_code == 200

    resp_new = client.get("/item/new")
    assert resp_new.status_code == 200

    resp_edit = client.get("/item/123/edit")
    assert resp_edit.status_code == 200


def test_profile_shell_routes(authed_client):
    client, _ = authed_client

    resp_profile = client.get("/profile")
    assert resp_profile.status_code == 200

    resp_edit = client.get("/profile/edit")
    assert resp_edit.status_code == 200


#########################
#       PROFILE API     #
#########################

def test_api_profile_me_returns_current_user(authed_client):
    client, user = authed_client

    resp = client.get("/api/profile/me")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "user" in data
    assert data["user"]["email"] == user.email


def test_api_profile_user_404_for_missing(authed_client):
    client, _ = authed_client

    resp = client.get("/api/profile/999999")
    assert resp.status_code == 404


def test_save_profile_edits_updates_bio(authed_client, app):
    client, user = authed_client
    new_bio = "Updated profile bio!"

    resp = client.post(
        "/profile/edit",
        data={"profile_description": new_bio},
        follow_redirects=False
    )
    assert resp.status_code in (302, 303)

    with app.app_context():
        refreshed = User.query.get(user.id)
        assert refreshed.profile_description == new_bio


########################################
#  ITEM LIST / GET / SEARCH / FILTER   #
########################################

def test_api_list_items_empty(authed_client):
    client, _ = authed_client
    resp = client.get("/api/items")
    assert resp.status_code == 200
    assert resp.get_json()["items"] == []


def test_api_list_items_with_item_and_bookmark(authed_client, app):
    client, user = authed_client

    with app.app_context():
        item = Item(
            seller_id=user.id,
            name="Desk",
            description="Study desk",
            price=50.0,
            condition="Good",
            payment_options=["Cash"],
            item_photos="/static/assets/item_placeholder.svg",
            bookmarked=True,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    # Use the real API to set the bookmark so it's stored
    resp_bm = client.post(
        "/api/bookmark",
        json={"item_id": item_id, "bookmarked": True},
    )
    assert resp_bm.status_code == 200

    resp = client.get("/api/items")
    assert resp.status_code == 200
    data = resp.get_json()

    assert len(data["items"]) == 1
    item_json = data["items"][0]
    assert item_json["id"] == item_id
    # Now the app’s own logic has set this flag
    assert item_json.get("bookmarked") is True

def test_api_list_items_filter_by_seller(authed_client, app):
    client, user = authed_client

    with app.app_context():
        my_item = Item(
            seller_id=user.id,
            name="My Item",
            description="mine",
            price=10.0,
            condition="Good",
            payment_options=["Cash"],
            item_photos="/static/assets/item_placeholder.svg"
        )
        db.session.add(my_item)

        other_user = User(
            email="other@colby.edu",
            first_name="Other",
            last_name="User"
        )
        other_user.set_password("pass")
        db.session.add(other_user)
        db.session.commit()

        other_item = Item(
            seller_id=other_user.id,
            name="Other Item",
            description="other",
            price=20.0,
            condition="Fair",
            payment_options=["Cash"],
            item_photos="/static/assets/item_placeholder.svg"
        )
        db.session.add(other_item)
        db.session.commit()

    resp = client.get(f"/api/items?seller_id={user.id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["items"]) == 2
    assert data["items"][0]["seller_id"] == user.id


def test_api_list_items_search_query(authed_client, app):
    client, user = authed_client

    with app.app_context():
        item1 = Item(
            seller_id=user.id,
            name="Red Desk",
            description="good for studying",
            price=30.0,
            condition="Good",
            payment_options=["Cash"],
            item_photos="/static/assets/item_placeholder.svg"
        )
        item2 = Item(
            seller_id=user.id,
            name="Blue Chair",
            description="comfy chair",
            price=20.0,
            condition="Fair",
            payment_options=["Cash"],
            item_photos="/static/assets/item_placeholder.svg"
        )
        db.session.add_all([item1, item2])
        db.session.commit()

    resp = client.get("/api/items?q=desk")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["items"]) == 2
    assert "Desk" in data["items"][0]["name"]


def test_api_get_item(authed_client, app):
    client, user = authed_client

    with app.app_context():
        item = Item(
            seller_id=user.id,
            name="Lamp",
            description="Desk lamp",
            price=12.5,
            condition="Like new",
            payment_options=["Cash"],
            item_photos="/static/assets/item_placeholder.svg"
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    resp = client.get(f"/api/items/{item_id}")
    assert resp.status_code == 200
    assert resp.get_json()["item"]["id"] == item_id


#########################
#     ITEM CREATION     #
#########################

def test_api_create_item_missing_name(authed_client):
    client, _ = authed_client

    resp = client.post(
        "/api/items",
        data={
            "description": "desc",
            "price": "5",
        },
        content_type="multipart/form-data"
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_api_create_item_invalid_price(authed_client):
    client, _ = authed_client
    resp = client.post(
        "/api/items",
        data={"name": "Book", "price": "asdf"},
        content_type="multipart/form-data"
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Price must be a number"


def test_api_create_item_negative_price(authed_client):
    client, _ = authed_client
    resp = client.post(
        "/api/items",
        data={"name": "Book", "price": "-5"},
        content_type="multipart/form-data"
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Price cannot be negative"


def test_api_create_item_success(authed_client, app):
    client, user = authed_client

    resp = client.post(
        "/api/items",
        data={
            "name": "Chair",
            "description": "Comfy chair",
            "price": "25",
            "condition": "Fair",
            "payment_options": ["Cash", "Venmo"]
        },
        content_type="multipart/form-data"
    )
    assert resp.status_code == 201

    item = resp.get_json()["item"]
    assert item["name"] == "Chair"
    assert item["price"] == 25.0

    with app.app_context():
        db_item = Item.query.get(item["id"])
        assert db_item is not None
        # Ensure the item is associated with the current user
        assert db_item.seller_id == user.id



#########################
#      ITEM UPDATE      #
#########################

def _create_item_for_user(app, user, **kwargs):
    with app.app_context():
        item = Item(
            seller_id=user.id,
            name=kwargs.get("name", "Item"),
            description=kwargs.get("description", "desc"),
            price=kwargs.get("price", 5.0),
            condition=kwargs.get("condition", "Good"),
            payment_options=kwargs.get("payment_options", ["Cash"]),
            item_photos=kwargs.get("item_photos", "/static/assets/item_placeholder.svg")
        )
        db.session.add(item)
        db.session.commit()
        return item.id


def test_api_update_item_forbidden(authed_client, app):
    client, user = authed_client

    with app.app_context():
        # Use a unique email so we don't collide with other tests
        other = User(email="other_forbidden@colby.edu", first_name="O", last_name="U")
        other.set_password("pass")
        db.session.add(other)
        db.session.commit()
        other_item_id = _create_item_for_user(app, other)

    resp = client.put(
        f"/api/items/{other_item_id}",
        data={"name": "Hack"},
        content_type="multipart/form-data"
    )
    assert resp.status_code == 403
    assert "error" in resp.get_json()


def test_api_update_item_invalid_price(authed_client, app):
    client, user = authed_client
    item_id = _create_item_for_user(app, user, price=5.0)

    resp = client.put(
        f"/api/items/{item_id}",
        data={"price": "notnum"},
        content_type="multipart/form-data"
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Price must be a number"


def test_api_update_item_negative_price(authed_client, app):
    client, user = authed_client
    item_id = _create_item_for_user(app, user)

    resp = client.put(
        f"/api/items/{item_id}",
        data={"price": "-2"},
        content_type="multipart/form-data"
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Price cannot be negative"


def test_api_update_item_success(authed_client, app):
    client, user = authed_client
    item_id = _create_item_for_user(app, user, name="Old", price=5.0)

    resp = client.put(
        f"/api/items/{item_id}",
        data={
            "name": "New",
            "description": "Updated",
            "price": "15",
            "condition": "Like new",
            "payment_options": ["Cash", "Venmo"]
        },
        content_type="multipart/form-data"
    )
    assert resp.status_code == 200
    updated = resp.get_json()["item"]
    assert updated["name"] == "New"
    assert updated["price"] == 15.0


#########################
#      ITEM DELETE      #
#########################

def test_api_delete_item_forbidden(authed_client, app):
    client, user = authed_client

    with app.app_context():
        other = User(email="someone@colby.edu", first_name="A", last_name="B")
        other.set_password("x")
        db.session.add(other)
        db.session.commit()
        other_item = _create_item_for_user(app, other)

    resp = client.delete(f"/api/items/{other_item}")
    assert resp.status_code == 403
    assert "error" in resp.get_json()


def test_api_delete_item_success(authed_client, app):
    client, user = authed_client
    item_id = _create_item_for_user(app, user)

    resp = client.delete(f"/api/items/{item_id}")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "deleted"

    with app.app_context():
        assert Item.query.get(item_id) is None


#########################
#       BOOKMARKS       #
#########################

def test_api_bookmark_invalid_payload(authed_client):
    client, _ = authed_client

    resp = client.post("/api/bookmark", json={})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_api_bookmark_invalid_item_id(authed_client):
    client, _ = authed_client

    resp = client.post("/api/bookmark", json={"item_id": "abc", "bookmarked": True})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "item_id must be an integer"


def test_api_bookmark_item_not_found(authed_client):
    client, _ = authed_client

    resp = client.post("/api/bookmark", json={"item_id": 999999, "bookmarked": True})
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Item not found"


def test_api_bookmark_toggle(authed_client, app):
    client, user = authed_client

    with app.app_context():
        item = Item(
            seller_id=user.id,
            name="Bookmark me",
            description="desc",
            price=10.0,
            condition="Good",
            payment_options=["Cash"],
            item_photos="/static/assets/item_placeholder.svg"
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    # add bookmark
    resp_add = client.post(
        "/api/bookmark",
        json={"item_id": item_id, "bookmarked": True}
    )
    assert resp_add.status_code == 200
    assert item_id in resp_add.get_json()["bookmarks"]

    # remove bookmark
    resp_remove = client.post(
        "/api/bookmark",
        json={"item_id": item_id, "bookmarked": False}
    )
    assert resp_remove.status_code == 200
    assert item_id not in resp_remove.get_json()["bookmarks"]
