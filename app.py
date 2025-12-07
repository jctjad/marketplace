from website import create_app, socketio
import os
from dotenv import load_dotenv
load_dotenv()

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, debug=True, port=port)
