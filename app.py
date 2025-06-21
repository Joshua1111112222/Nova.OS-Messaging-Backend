from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import time

app = Flask(__name__)
CORS(app)

# In-memory storage (replace with DB in prod)
users = {}
sessions = {}  # token: username
messages = []

# Hardcoded admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("Pusheen#99")

# Helper: check admin token
def is_admin(token):
    username = sessions.get(token)
    if not username:
        return False
    if username != ADMIN_USERNAME:
        return False
    return True

# --- Auth ---

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    if username in users:
        return jsonify({"success": False, "error": "Username already exists"}), 400

    password_hash = generate_password_hash(password)
    users[username] = {"password": password_hash, "created": time.time()}
    return jsonify({"success": True, "message": "User created"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    if username not in users:
        return jsonify({"success": False, "error": "Invalid username or password"}), 401

    if username == ADMIN_USERNAME:
        # Special admin check
        if not check_password_hash(ADMIN_PASSWORD_HASH, password):
            return jsonify({"success": False, "error": "Invalid admin password"}), 401
    else:
        if not check_password_hash(users[username]["password"], password):
            return jsonify({"success": False, "error": "Invalid username or password"}), 401

    # Create session token
    token = secrets.token_hex(16)
    sessions[token] = username
    return jsonify({"success": True, "token": token, "username": username}), 200

# --- User management (admin only) ---

@app.route('/users', methods=['GET'])
def list_users():
    token = request.headers.get("Authorization")
    if not is_admin(token):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    user_list = list(users.keys())
    return jsonify({"success": True, "users": user_list})

@app.route('/users/<username>', methods=['DELETE'])
def delete_user(username):
    token = request.headers.get("Authorization")
    if not is_admin(token):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    if username == ADMIN_USERNAME:
        return jsonify({"success": False, "error": "Cannot delete admin user"}), 403
    if username in users:
        users.pop(username)
        # Also remove any sessions of deleted user
        tokens_to_delete = [t for t, u in sessions.items() if u == username]
        for t in tokens_to_delete:
            sessions.pop(t)
        # Optionally remove messages by that user
        global messages
        messages = [m for m in messages if m.get("user") != username]
        return jsonify({"success": True, "message": f"User '{username}' deleted"}), 200
    return jsonify({"success": False, "error": "User not found"}), 404

# --- Messages ---

@app.route('/messages', methods=['GET'])
def get_messages():
    token = request.headers.get("Authorization")
    if token not in sessions:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify(messages)

@app.route('/messages', methods=['POST'])
def send_message():
    token = request.headers.get("Authorization")
    if token not in sessions:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = request.json
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"success": False, "error": "Empty message"}), 400

    user = sessions[token]
    message = {
        "user": user,
        "text": text,
        "timestamp": time.time()
    }
    messages.append(message)
    return jsonify({"success": True, "message": "Message sent"}), 201

@app.route('/messages/<int:index>', methods=['DELETE'])
def delete_message(index):
    token = request.headers.get("Authorization")
    if token not in sessions:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    user = sessions[token]
    if index < 0 or index >= len(messages):
        return jsonify({"success": False, "error": "Invalid message index"}), 400

    message = messages[index]
    # Only admin or the user who sent the message can delete it
    if user != message["user"] and user != ADMIN_USERNAME:
        return jsonify({"success": False, "error": "Not authorized to delete this message"}), 403

    messages.pop(index)
    return jsonify({"success": True, "message": "Message deleted"}), 200

@app.route('/messages/<int:index>', methods=['PUT'])
def edit_message(index):
    token = request.headers.get("Authorization")
    if token not in sessions:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    user = sessions[token]
    if index < 0 or index >= len(messages):
        return jsonify({"success": False, "error": "Invalid message index"}), 400

    message = messages[index]
    if user != message["user"] and user != ADMIN_USERNAME:
        return jsonify({"success": False, "error": "Not authorized to edit this message"}), 403

    data = request.json
    new_text = data.get("text", "").strip()
    if not new_text:
        return jsonify({"success": False, "error": "Empty message"}), 400

    messages[index]["text"] = new_text
    return jsonify({"success": True, "message": "Message updated"}), 200


if __name__ == '__main__':
    app.run(debug=True)
