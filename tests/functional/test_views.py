
def test_join(test_socketio_client):
    """
    GIVEN
    WHEN
    THEN
    """



def test_message(test_socketio_client, test_data_socketio):
    """
    GIVEN
    WHEN
    THEN
    """
    user1 = test_data_socketio['user1']
    user2 = test_data_socketio['user2']
    item = test_data_socketio['item']

    test_socketio_client.emit("message", {"text": "hello"})

    received = test_socketio_client.get_received()
    assert len(received) > 0

    event = received[0]
    assert event["name"] == "message"
    assert event["args"][0]["text"] == "hello"


def test_disconnect(test_socketio_client):
    """
    GIVEN
    WHEN
    THEN
    """