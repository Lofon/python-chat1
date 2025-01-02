from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random

app = Flask(__name__)
socketio = SocketIO(app)

# Lưu trữ thông tin người dùng và phòng chat
users = {}  # socket_id: {username, gender, avatar}
rooms = {}  # room_name: {password, private, users (list of socket_ids)}

@app.route('/')
def index():
    return render_template('index.html')

# Khi người dùng kết nối
@socketio.on("connect")
def handle_connect():
    emit("request_user_info")  # Gửi yêu cầu cung cấp thông tin người dùng

# Khi người dùng gửi thông tin
@socketio.on("user_info")
def handle_user_info(data):
    username = data["username"]
    gender = data["gender"]
    avatar_id = data["avatar_id"]
    avatar_url = f"https://avatar.iran.liara.run/public/{gender}?username={username}"
    
    users[request.sid] = {
        "username": username,
        "gender": gender,
        "avatar": avatar_url
    }

    emit("user_joined", {"username": username, "avatar": avatar_url}, broadcast=True)

# Khi người dùng ngắt kết nối
@socketio.on("disconnect")
def handle_disconnect():
    user = users.pop(request.sid, None)
    if user:
        emit("user_left", {"username": user["username"]}, broadcast=True)

# Khi người dùng gửi tin nhắn
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

# Khi người dùng tạo phòng chat
@socketio.on("create_room")
def handle_create_room(data):
    room_name = data["room_name"]
    password = data.get("password", None)
    private = data.get("private", False)

    if room_name not in rooms:
        rooms[room_name] = {
            "password": password,
            "private": private,
            "users": []
        }
        emit("room_created", {"room_name": room_name}, broadcast=True)

# Khi người dùng tham gia phòng chat
@socketio.on("join_room")
def handle_join_room(data):
    room_name = data["room_name"]
    password = data.get("password", None)

    if room_name in rooms:
        room = rooms[room_name]
        if room["private"] and room["password"] != password:
            emit("join_failed", {"reason": "Sai mật khẩu"})
        else:
            room["users"].append(request.sid)
            join_room(room_name)
            emit("joined_room", {"room_name": room_name}, room=request.sid)
            emit("user_joined_room", {"username": users[request.sid]["username"]}, room=room_name)

# Khi người dùng rời phòng chat
@socketio.on("leave_room")
def handle_leave_room(data):
    room_name = data["room_name"]

    if room_name in rooms:
        room = rooms[room_name]
        if request.sid in room["users"]:
            room["users"].remove(request.sid)
            leave_room(room_name)
            emit("user_left_room", {"username": users[request.sid]["username"]}, room=room_name)

if __name__ == "__main__":
    socketio.run(app)
