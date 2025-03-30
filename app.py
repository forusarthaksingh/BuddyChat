from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite3"
app.config["UPLOAD_FOLDER"] = "uploads"

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Ensure upload folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# ---------------- DATABASE MODELS ---------------- #
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), unique=False, nullable=False)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ---------------- FUNCTION TO LOG IP ADDRESSES ---------------- #
import os

# Function to log user IP
def log_ip(username):
    user_ip = request.remote_addr  # Get user's IP address
    log_entry = f"{datetime.utcnow()} - {username} - {user_ip}\n"
    file_path = "ips.txt"  # Define file name

    try:
        # Ensure file is created and opened in append mode
        with open(file_path, "a+") as file:  # "a+" creates the file if it doesn’t exist
            file.seek(0)  # Move to the start of the file
            logged_ips = file.readlines()  # Read existing IPs

            # Avoid duplicate IP logging
            if log_entry not in logged_ips:
                file.write(log_entry)  # Append new IP entry

        print(f"✅ IP Logged: {log_entry.strip()}")  # Debugging message

    except Exception as e:
        print(f"⚠️ Error writing to ips.txt: {e}")  # Error handling


# ---------------- AUTH ROUTES ---------------- #
@app.route("/", methods=["GET", "POST"])
def index():
    if "user" in session:
        return redirect(url_for("chat"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session["user"] = username
            log_ip(username)  # Log IP on successful login
            return redirect(url_for("chat"))
        else:
            flash("Invalid username or password", "danger")

    return render_template("index.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
            return redirect(url_for("signup"))

        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        
        return redirect(url_for("index"))

    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

# ---------------- CHAT & ROOM ROUTES ---------------- #

@app.route("/chat")
def chat():
    if "user" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("index"))

    print(f"User {session['user']} accessed chat.")  # Debugging
    rooms = Room.query.all()
    return render_template("chat.html", username=session["user"], rooms=rooms)

@app.route("/room/<room_name>")
def room(room_name):
    if "user" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("index"))

    room = Room.query.filter_by(name=room_name).first()
    if not room:
        flash("Room not found!", "danger")
        return redirect(url_for("chat"))

    print(f"User {session['user']} entered room {room_name}")  # Debugging
    messages = Message.query.filter_by(room=room_name).order_by(Message.timestamp).all()
    return render_template("room.html", username=session["user"], room=room_name, messages=messages)


@app.route("/create_room", methods=["POST"])
def create_room():
    if "user" not in session:
        return redirect(url_for("index"))

    room_name = request.form["room_name"]
    password = generate_password_hash(request.form["room_password"], method="pbkdf2:sha256")

    existing_room = Room.query.filter_by(name=room_name).first()
    if existing_room:
        flash("Room name already exists!", "danger")
        return redirect(url_for("chat"))

    new_room = Room(name=room_name, password=password)
    db.session.add(new_room)
    db.session.commit()

    # Store the room in session
    session["room"] = room_name
    return redirect(url_for("room", room_name=room_name))



@app.route("/join_room", methods=["POST"])
def join_room_route():
    if "user" not in session:
        return redirect(url_for("index"))

    room_name = request.form["room_name"]
    room_password = request.form["room_password"]
    room = Room.query.filter_by(name=room_name).first()

    if not room:
        flash("Room not found!", "danger")
        return redirect(url_for("chat"))

    print(f"Joining room: {room_name}, Entered Password: {room_password}")  # Debugging

    if check_password_hash(room.password, room_password):
        session["room"] = room_name
        return redirect(url_for("room", room_name=room_name))
    else:
        flash("Invalid room name or password!", "danger")
        return redirect(url_for("chat"))



# ---------------- SOCKET EVENTS ---------------- #
@socketio.on("join")
def handle_join(data):
    if "user" not in session:
        return

    username = session["user"]
    room = data["room"]

    join_room(room)
    send({"username": "System", "message": f"{username} joined the chat"}, room=room)
    print(f"User {username} joined room {room}")  # Debugging


@socketio.on("leave")
def handle_leave(data):
    username = session["user"]
    room = data["room"]
    leave_room(room)
    send({"username": "System", "message": f"{username} left the chat"}, room=room)

@socketio.on("message")
def handle_message(data):
    room = data["room"]
    message = data["message"]
    username = session["user"]

    new_message = Message(room=room, username=username, message=message)
    db.session.add(new_message)
    db.session.commit()

    send({"username": username, "message": message}, room=room)



# ---------------- START APP ---------------- #
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
    

    
