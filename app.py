from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
socketio = SocketIO(app)

# Dictionary to store rooms and users
rooms = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on("connect")
def handle_connect():
    session_id = request.sid
    print(f"New connection: {session_id}")

@socketio.on("set_username")
def set_username(data):
    username = data["username"]
    gender = data.get("gender", "boy")  # Default to boy if gender is not provided
    emit("set_user_info", {"username": username, "gender": gender})

@socketio.on("create_room")
def handle_create_room(data):
    room_id = f"Room_{random.randint(1000, 9999)}"
    room_name = data["room_name"]
    room_type = data["room_type"]
    room_password = data.get("room_password", None)

    rooms[room_id] = {
        "room_name": room_name,
        "room_type": room_type,
        "room_password": generate_password_hash(room_password) if room_password else None,
        "users": {}
    }

    emit("room_created", {"room_id": room_id, "room_name": room_name})

@socketio.on("join_room")
def handle_join_room(data):
    room_id = data["room_id"]
    username = data["username"]
    gender = data.get("gender", "boy")  # Default to boy if gender is not provided
    password = data.get("password", None)

    if room_id in rooms:
        room = rooms[room_id]
        if room["room_type"] == "private" and not check_password_hash(room["room_password"], password):
            emit("join_error", {"error": "Invalid password"})
            return

        join_room(room_id)
        room["users"][request.sid] = {"username": username, "gender": gender}
        emit("room_joined", {"room_id": room_id, "room_name": room["room_name"], "users": list(room["users"].values())})
        emit("user_joined_room", {"username": username}, room=room_id)

@socketio.on("leave_room")
def handle_leave_room(data):
    room_id = data["room_id"]
    user = rooms[room_id]["users"].pop(request.sid, None)

    if user:
        leave_room(room_id)
        emit("user_left_room", {"username": user["username"]}, room=room_id)
        if not rooms[room_id]["users"]:
            rooms.pop(room_id)
            emit("room_closed", {"room_id": room_id})

@socketio.on("send_message")
def handle_send_message(data):
    room_id = data["room_id"]
    user = rooms[room_id]["users"].get(request.sid)
    if user:
        timestamp = datetime.now().strftime('%H:%M:%S')
        emit("new_message", {
            "username": user["username"],
            "avatar": f"https://avatar.iran.liara.run/public/{user['gender']}?username={user['username']}",
            "message": data["message"],
            "timestamp": timestamp
        }, room=room_id)

@socketio.on("update_username")
def handle_update_username(data):
    new_username = data["username"]
    new_gender = data.get("gender", None)
    for room in rooms.values():
        if request.sid in room["users"]:
            old_user = room["users"][request.sid]
            room["users"][request.sid]["username"] = new_username
            if new_gender:
                room["users"][request.sid]["gender"] = new_gender
            emit("username_updated", {
                "old_username": old_user["username"],
                "new_username": new_username,
                "new_gender": new_gender
            }, room=request.sid)

@socketio.on("get_rooms")
def handle_get_rooms():
    available_rooms = [
        {"room_id": room_id, "room_name": room["room_name"], "room_type": room["room_type"]}
        for room_id, room in rooms.items()
    ]
    emit("rooms_list", {"rooms": available_rooms})

if __name__ == "__main__":
    socketio.run(app)
