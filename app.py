from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import random

app = Flask(__name__)
socketio = SocketIO(app)

# Lưu trữ người dùng và thông tin các room chat
users = {}
rooms = {}  # Tên room: {password, private, users}

@app.route('/')
def index():
    return render_template('index.html')

# Sự kiện khi người dùng kết nối
@socketio.on("connect")
def handle_connect():
    emit("request_user_info")  # Yêu cầu người dùng chọn tên, giới tính, avatar

@socketio.on("user_info")
def handle_user_info(data):
    users[request.sid] = {
        "username": data["username"],
        "avatar": data["avatar"],
        "gender": data["gender"]
    }
    emit("user_joined", {"username": data["username"], "avatar": data["avatar"]}, broadcast=True)

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
            "time": data["time"]  # Thời gian gửi tin nhắn
        }, broadcast=True)

@socketio.on("update_username")
def handle_update_username(data):
    old_username = users[request.sid]["username"]
    new_username = data["username"]
    users[request.sid]["username"] = new_username
    emit("username_updated", {"old_username": old_username, "new_username": new_username}, broadcast=True)

# Room chat logic
@socketio.on("create_room")
def handle_create_room(data):
    room_name = data["room_name"]
    password = data.get("password", None)
    private = data.get("private", False)
    rooms[room_name] = {"password": password, "private": private, "users": []}
    emit("room_created", {"room_name": room_name}, broadcast=True)

@socketio.on("join_room")
def handle_join_room(data):
    room_name = data["room_name"]
    password = data.get("password", None)
    if room_name in rooms:
        if rooms[room_name]["private"] and rooms[room_name]["password"] != password:
            emit("join_failed", {"reason": "Wrong password"})
        else:
            rooms[room_name]["users"].append(request.sid)
            emit("joined_room", {"room_name": room_name})
            socketio.enter_room(request.sid, room_name)
            emit("user_joined_room", {"username": users[request.sid]["username"], "room_name": room_name}, room=room_name)

@socketio.on("leave_room")
def handle_leave_room(data):
    room_name = data["room_name"]
    if room_name in rooms:
        rooms[room_name]["users"].remove(request.sid)
        emit("user_left_room", {"username": users[request.sid]["username"], "room_name": room_name}, room=room_name)
        socketio.leave_room(request.sid, room_name)

@socketio.on("vote_kick")
def handle_vote_kick(data):
    room_name = data["room_name"]
    user_to_kick = data["username"]
    if room_name in rooms:
        vote_count = data["votes"]
        if vote_count >= len(rooms[room_name]["users"]) // 2:
            # Kick user
            for sid, user in users.items():
                if user["username"] == user_to_kick:
                    emit("user_kicked", {"username": user_to_kick, "room_name": room_name}, room=room_name)
                    rooms[room_name]["users"].remove(sid)
                    socketio.leave_room(sid, room_name)
                    break

if __name__ == "__main__":
    socketio.run(app)
