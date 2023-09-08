
from flask_socketio import SocketIO

socketio = SocketIO(app, cors_allowed_origins=['http://localhost:3000'], async_mode='threading', transports=['websocket'])
