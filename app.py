from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import datetime

app = Flask(__name__)
socketio = SocketIO(app)

# Store connected users. Key is socket id, value is user details
users = {}

# Store chat rooms. Key is room name, value is room details
rooms = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on("connect")
def handle_connect():
    emit("prompt_username_gender")

@socketio.on("set_username_gender")
def handle_set_username_gender(data):
    username = data.get("username")
    gender = data.get("gender")
    avatar_url = f"https://avatar.iran.liara.run/public/{gender}?username={username}"
    users[request.sid] = {"username": username, "avatar": avatar_url}

    emit("user_joined", {"username": username, "avatar": avatar_url}, broadcast=True)
    emit("set_username", {"username": username})

@socketio.on("disconnect")
def handle_disconnect():
    user = users.pop(request.sid, None)
    if user:
        emit("user_left", {"username": user["username"]}, broadcast=True)

@socketio.on("send_message")
def handle_message(data):
    user = users.get(request.sid)
    if user:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        emit("new_message", {
            "username": user["username"],
            "avatar": user["avatar"],
            "message": data["message"],
            "timestamp": timestamp
        }, room=data["room"])

@socketio.on("update_username")
def handle_update_username(data):
    old_username = users[request.sid]["username"]
    new_username = data["username"]
    users[request.sid]["username"] = new_username

    emit("username_updated", {
        "old_username": old_username,
        "new_username": new_username
    }, broadcast=True)

@socketio.on("create_room")
def handle_create_room(data):
    room_name = data["room_name"]
    password = data.get("password")
    rooms[room_name] = {"password": password, "members": []}
    emit("room_created", {"room_name": room_name}, broadcast=True)

@socketio.on("join_room")
def handle_join_room(data):
    room_name = data["room_name"]
    password = data.get("password")
    room = rooms.get(room_name)

    if room and (room["password"] == password or room["password"] is None):
        join_room(room_name)
        room["members"].append(request.sid)
        emit("joined_room", {"room_name": room_name, "username": users[request.sid]["username"]}, room=room_name)
    else:
        emit("join_error", {"message": "Incorrect password or room does not exist"})

@socketio.on("leave_room")
def handle_leave_room(data):
    room_name = data["room_name"]
    room = rooms.get(room_name)

    if room:
        leave_room(room_name)
        room["members"].remove(request.sid)
        emit("left_room", {"room_name": room_name, "username": users[request.sid]["username"]}, room=room_name)

if __name__ == "__main__":
    socketio.run(app)
