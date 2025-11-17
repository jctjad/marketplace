# added this file to fix circular import issue

from flask import Flask
from flask_socketio import SocketIO, send, emit, join_room, leave_room

app = Flask(__name__)

socketio = SocketIO(app) # wrapping our app in SocektIO to enable WebSocket capabilities