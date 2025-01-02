from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import datetime

app = Flask(__name__)
socketio = SocketIO(app)

# Lưu trữ thông tin người dùng và phòng chat
users = {}  # socket_id: {username, gender, room}
rooms = {}  # room_name: {password, private, users (list of socket_ids)}

@app.route('/')
def index():
    return render_template('index.html')

# Khi người dùng kết nối
@socketio.on("connect")
def handle_connect():
    emit("request_user_info")  # Yêu cầu người dùng nhập thông tin

# Khi người dùng gửi thông tin
@socketio.on("user_info")
def handle_user_info(data):
    username = data["username"]
    gender = data["gender"]
    users[request.sid] = {
        "username": username,
        "gender": gender,
        "room": None
    }
    emit("user_joined", {"username": username}, broadcast=True)

# Khi người dùng ngắt kết nối
@socketio.on("disconnect")
def handle_disconnect():
    user = users.pop(request.sid, None)
    if user and user["room"]:
        room_name = user["room"]
        rooms[room_name]["users"].remove(request.sid)
        emit("user_left_room", {"username": user["username"]}, room=room_name)
        if not rooms[room_name]["users"]:  # Xóa room nếu không còn ai
            del rooms[room_name]

# Gửi tin nhắn
@socketio.on("send_message")
def handle_message(data):
    user = users.get(request.sid)
    if user and user["room"]:
        room_name = user["room"]
        time = datetime.datetime.now().strftime("%H:%M:%S")
        emit("new_message", {
            "username": user["username"],
            "message": data["message"],
            "time": time
        }, room=room_name)

# Tạo phòng chat
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

# Tham gia phòng chat
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
            users[request.sid]["room"] = room_name
            join_room(room_name)
            emit("joined_room", {"room_name": room_name}, room=request.sid)
            emit("user_joined_room", {"username": users[request.sid]["username"]}, room=room_name)

# Rời phòng chat
@socketio.on("leave_room")
def handle_leave_room(data):
    room_name = data["room_name"]

    if room_name in rooms:
        room = rooms[room_name]
        if request.sid in room["users"]:
            room["users"].remove(request.sid)
            users[request.sid]["room"] = None
            leave_room(room_name)
            emit("user_left_room", {"username": users[request.sid]["username"]}, room=room_name)

# Lấy danh sách phòng
@socketio.on("get_rooms")
def handle_get_rooms():
    room_list = [{"name": room, "private": info["private"]} for room, info in rooms.items()]
    emit("room_list", {"rooms": room_list})

if __name__ == "__main__":
    socketio.run(app)
