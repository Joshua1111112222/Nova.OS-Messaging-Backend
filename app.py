from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

# SQLite config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///messages_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Admin credentials (hardcoded)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("Pusheen#99")

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(80), nullable=False)
    text = db.Column(db.Text, nullable=False)

# Create tables if not exists
with app.app_context():
    db.create_all()

# Register new user
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400

    if username == ADMIN_USERNAME:
        return jsonify({"success": False, "error": "Cannot register as admin"}), 403

    if User.query.filter_by(username=username).first():
        return jsonify({"success": False, "error": "Username taken"}), 409

    user = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()

    return jsonify({"success": True, "message": "Registered successfully"})

# Login user/admin
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400

    if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
        return jsonify({"success": True, "admin": True, "username": ADMIN_USERNAME})

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return jsonify({"success": True, "admin": False, "username": username})

    return jsonify({"success": False, "error": "Invalid credentials"}), 401

# Get all messages
@app.route('/messages', methods=['GET'])
def get_messages():
    msgs = Message.query.order_by(Message.id.asc()).all()
    return jsonify([{"id": m.id, "user": m.user, "text": m.text} for m in msgs])

# Send message
@app.route('/messages', methods=['POST'])
def send_message():
    data = request.json
    user = data.get("user")
    text = data.get("text")

    if not user or not text:
        return jsonify({"success": False, "error": "User and text required"}), 400

    msg = Message(user=user, text=text)
    db.session.add(msg)
    db.session.commit()

    return jsonify({"success": True, "message": "Message sent"})

# Delete user (admin only)
@app.route('/admin/delete_user', methods=['POST'])
def delete_user():
    data = request.json
    admin_username = data.get("admin_username")
    admin_password = data.get("admin_password")
    username_to_delete = data.get("username")

    if admin_username != ADMIN_USERNAME or not check_password_hash(ADMIN_PASSWORD_HASH, admin_password):
        return jsonify({"success": False, "error": "Admin authentication failed"}), 403

    user = User.query.filter_by(username=username_to_delete).first()
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"success": True, "message": f"User {username_to_delete} deleted"})

# List all users (admin only)
@app.route('/admin/list_users', methods=['GET'])
def list_users():
    admin_username = request.args.get("admin_username")
    admin_password = request.args.get("admin_password")

    if admin_username != ADMIN_USERNAME or not check_password_hash(ADMIN_PASSWORD_HASH, admin_password):
        return jsonify({"success": False, "error": "Admin authentication failed"}), 403

    users = User.query.all()
    return jsonify([u.username for u in users])

if __name__ == '__main__':
    app.run(debug=True)
