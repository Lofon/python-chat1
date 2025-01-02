from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import random

app = Flask(__name__)
socketio = SocketIO(app)

# python dict. Store connected users. Key is socket id, value is username and avatarUrl 
users = {}
rooms = {}  # Stores room info

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on("connect")
def handle_connect():
    emit("prompt_user_info")

@socketio.on("user_info")
def handle_user_info(data):
    username = data["username"]
    gender = data["gender"]
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
        emit("new_message", {
            "username": user["username"],
            "avatar": user["avatar"],
            "message": data["message"],
            "time": data["time"]
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
    private = data["private"]
    password = data["password"] if private else None
    rooms[room_name] = {"private": private, "password": password, "users": []}
    emit("room_created", {"room_name": room_name})

@socketio.on("join_room")
def handle_join_room(data):
    room_name = data["room_name"]
    room = rooms.get(room_name)
    if room:
        if room["private"] and room["password"] != data["password"]:
            emit("join_error", {"error": "Incorrect password"})
        else:
            rooms[room_name]["users"].append(request.sid)
            join_room(room_name)
            emit("room_joined", {"room_name": room_name})
            emit("user_joined_room", {"username": users[request.sid]["username"]}, room=room_name)
    else:
        emit("join_error", {"error": "Room not found"})

@socketio.on("leave_room")
def handle_leave_room(data):
    room_name = data["room_name"]
    if room_name in rooms:
        rooms[room_name]["users"].remove(request.sid)
        leave_room(room_name)
        emit("room_left", {"room_name": room_name})
        emit("user_left_room", {"username": users[request.sid]["username"]}, room=room_name)

if __name__ == "__main__":
    socketio.run(app)
