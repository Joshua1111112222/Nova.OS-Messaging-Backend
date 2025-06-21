from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import uuid

app = Flask(__name__)
CORS(app)

USERS_FILE = "users.json"
MESSAGES_FILE = "messages.json"

# Load users
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
else:
    users = {}

# Load messages
if os.path.exists(MESSAGES_FILE):
    with open(MESSAGES_FILE, "r") as f:
        messages = json.load(f)
else:
    messages = []

def save_messages():
    with open(MESSAGES_FILE, "w") as f:
        json.dump(messages, f)

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"success": False, "error": "Missing username or password"}), 400
    if username in users:
        return jsonify({"success": False, "error": "User already exists"}), 400
    users[username] = password
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)
    return jsonify({"success": True}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if users.get(username) == password:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route("/messages", methods=["GET"])
def get_messages():
    return jsonify(messages)

@app.route("/messages", methods=["POST"])
def post_message():
    data = request.json
    username = data.get("user")
    password = data.get("password")
    text = data.get("text")

    if not username or not password or not text:
        return jsonify({"success": False, "error": "Missing data"}), 400
    if users.get(username) != password:
        return jsonify({"success": False, "error": "Authentication failed"}), 401

    message_id = str(uuid.uuid4())
    msg = {"id": message_id, "user": username, "text": text}
    messages.append(msg)
    save_messages()
    return jsonify({"success": True, "message": "Message stored", "id": message_id}), 201

@app.route("/messages/<msg_id>", methods=["DELETE"])
def delete_message(msg_id):
    data = request.json
    username = data.get("user")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "error": "Missing auth data"}), 400
    if users.get(username) != password:
        return jsonify({"success": False, "error": "Authentication failed"}), 401

    global messages
    for i, msg in enumerate(messages):
        if msg["id"] == msg_id:
            if msg["user"] != username:
                return jsonify({"success": False, "error": "Not authorized to delete this message"}), 403
            del messages[i]
            save_messages()
            return jsonify({"success": True, "message": "Message deleted"})
    return jsonify({"success": False, "error": "Message not found"}), 404

@app.route("/messages/<msg_id>", methods=["PUT"])
def edit_message(msg_id):
    data = request.json
    username = data.get("user")
    password = data.get("password")
    new_text = data.get("text")

    if not username or not password or new_text is None:
        return jsonify({"success": False, "error": "Missing data"}), 400
    if users.get(username) != password:
        return jsonify({"success": False, "error": "Authentication failed"}), 401

    for msg in messages:
        if msg["id"] == msg_id:
            if msg["user"] != username:
                return jsonify({"success": False, "error": "Not authorized to edit this message"}), 403
            msg["text"] = new_text
            save_messages()
            return jsonify({"success": True, "message": "Message updated"})
    return jsonify({"success": False, "error": "Message not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)
