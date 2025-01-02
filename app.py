from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
from datetime import datetime

app = Flask(__name__) 
socketio = SocketIO(app)

# Dictionary to store rooms and users
rooms = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on("connect")
def handle_connect():
    username = f"User_{random.randint(1000,9999)}"
    gender = random.choice(["girl", "boy"])
    avatar_url = f"https://avatar.iran.liara.run/public/{gender}?username={username}"
    emit("set_user_info", {"username": username, "gender": gender})

@socketio.on("create_room")
def handle_create_room(data):
    room_id = f"Room_{random.randint(1000,9999)}"
    room_name = data["room_name"]
    room_type = data["room_type"]
    room_password = data.get("room_password", None)

    rooms[room_id] = {
        "room_name": room_name,
        "room_type": room_type,
        "room_password": room_password if room_type == "private" else None,
        "users": {}
    }

    emit("room_created", {"room_id": room_id, "room_name": room_name})

@socketio.on("join_room")
def handle_join_room(data):
    room_id = data["room_id"]
    username = data["username"]
    password = data.get("password", None)

    if room_id in rooms:
        room = rooms[room_id]
        if room["room_type"] == "private" and room["room_password"] != password:
            emit("join_error", {"error": "Invalid password"})
            return

        join_room(room_id)
        room["users"][request.sid] = username
        emit("room_joined", {"room_id": room_id, "room_name": room["room_name"], "users": list(room["users"].values())})
        emit("user_joined_room", {"username": username}, room=room_id)

@socketio.on("leave_room")
def handle_leave_room(data):
    room_id = data["room_id"]
    username = rooms[room_id]["users"].pop(request.sid, None)

    if username:
        leave_room(room_id)
        emit("user_left_room", {"username": username}, room=room_id)
        if not rooms[room_id]["users"]:
            rooms.pop(room_id)
            emit("room_closed", {"room_id": room_id})

@socketio.on("send_message")
def handle_send_message(data):
    room_id = data["room_id"]
    username = rooms[room_id]["users"].get(request.sid)
    if username:
        timestamp = datetime.now().strftime('%H:%M:%S')
        emit("new_message", {
            "username": username,
            "avatar": f"https://avatar.iran.liara.run/public/{random.choice(['boy', 'girl'])}?username={username}",
            "message": data["message"],
            "timestamp": timestamp
        }, room=room_id)

@socketio.on("update_username")
def handle_update_username(data):
    for room in rooms.values():
        if request.sid in room["users"]:
            old_username = room["users"][request.sid]
            new_username = data["username"]
            room["users"][request.sid] = new_username
            emit("username_updated", {
                "old_username": old_username,
                "new_username": new_username
            }, room=request.sid)

@socketio.on("update_room_password")
def handle_update_room_password(data):
    room_id = data["room_id"]
    new_password = data["new_password"]
    if room_id in rooms and rooms[room_id]["room_type"] == "private":
        rooms[room_id]["room_password"] = new_password
        emit("room_password_updated", {"room_id": room_id})

@socketio.on("get_room_users")
def handle_get_room_users(data):
    room_id = data["room_id"]
    if room_id in rooms:
        users = list(rooms[room_id]["users"].values())
        emit("room_users", {"room_id": room_id, "users": users})

@socketio.on("get_rooms")
def handle_get_rooms():
    available_rooms = [
        {"room_id": room_id, "room_name": room["room_name"], "room_type": room["room_type"]}
        for room_id, room in rooms.items()
    ]
    emit("rooms_list", {"rooms": available_rooms})

if __name__ == "__main__":
    socketio.run(app)
