"""test_views.py"""

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