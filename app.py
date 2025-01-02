from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import random

app = Flask(__name__)
socketio = SocketIO(app)

# Python dict để lưu trữ người dùng kết nối. Key là socket id, giá trị là username, avatarUrl, gender
users = {}

# Python dict để lưu trữ các phòng chat. Key là room name, giá trị là danh sách người dùng
rooms = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on("connect")
def handle_connect():
    emit("request_username")

@socketio.on("set_user_info")
def handle_set_user_info(data):
    users[request.sid] = { 
        "username": data["username"],
        "avatar": f"https://avatar.iran.liara.run/public/{data['gender']}?username={data['username']}",
        "gender": data["gender"]
    }
    emit("user_joined", {"username": data["username"], "avatar": users[request.sid]["avatar"]}, broadcast=True)
    emit("set_username", {"username": data["username"]})

@socketio.on("disconnect")
def handle_disconnect():
    user = users.pop(request.sid, None)
    if user:
        emit("user_left", {"username": user["username"]}, broadcast=True)
        for room in rooms.values():
            if user["username"] in room:
                room.remove(user["username"])
                break

@socketio.on("send_message")
def handle_message(data):
    user = users.get(request.sid)
    if user:
        emit("new_message", {
            "username": user["username"],
            "avatar": user["avatar"],
            "message": data["message"],
            "timestamp": data["timestamp"]
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
    if room_name not in rooms:
        rooms[room_name] = []
        if data["private"]:
            rooms[room_name] = data["password"]
        emit("room_created", {"room_name": room_name, "private": data["private"]}, broadcast=True)

@socketio.on("join_room")
def handle_join_room(data):
    room_name = data["room_name"]
    password = data.get("password")
    if room_name in rooms:
        if isinstance(rooms[room_name], list) or rooms[room_name] == password:
            users[request.sid]["room"] = room_name
            rooms[room_name].append(users[request.sid]["username"])
            emit("room_joined", {"room_name": room_name}, room=room_name)
            socketio.enter_room(request.sid, room_name)
        else:
            emit("join_failed", {"message": "Incorrect password"})

if __name__ == "__main__":
    socketio.run(app)
