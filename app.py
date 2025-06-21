from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # allow all origins for testing

# SQLite config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///messages_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Admin credentials (plain text)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Pusheen#99"

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # plain text, insecure

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(80), nullable=False)
    text = db.Column(db.Text, nullable=False)

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

    user = User(username=username, password=password)
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

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return jsonify({"success": True, "admin": True, "username": ADMIN_USERNAME})

    user = User.query.filter_by(username=username).first()
    if user and user.password == password:
        return jsonify({"success": True, "admin": False, "username": username})

    return jsonify({"success": False, "error": "Invalid credentials"}), 401

# Get all messages
@app.route('/messages', methods=['GET'])
def get_messages():
    messages = Message.query.order_by(Message.id.asc()).all()
    return jsonify([{"user": m.user, "text": m.text} for m in messages])

# Post a new message
@app.route('/messages', methods=['POST'])
def post_message():
    data = request.json
    user = data.get("user")
    text = data.get("text")

    if not user or not text:
        return jsonify({"success": False, "error": "User and text required"}), 400

    msg = Message(user=user, text=text)
    db.session.add(msg)
    db.session.commit()

    return jsonify({"success": True})

# Admin: list users
@app.route('/admin/list_users', methods=['GET'])
def list_users():
    admin_username = request.args.get("admin_username")
    admin_password = request.args.get("admin_password")

    if admin_username != ADMIN_USERNAME or admin_password != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    users = [u.username for u in User.query.all()]
    users.append(ADMIN_USERNAME)  # Add admin explicitly
    return jsonify(users)

# Admin: delete a user and their messages
@app.route('/admin/delete_user', methods=['POST'])
def delete_user():
    data = request.json
    admin_username = data.get("admin_username")
    admin_password = data.get("admin_password")
    username = data.get("username")

    if admin_username != ADMIN_USERNAME or admin_password != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    if username == ADMIN_USERNAME:
        return jsonify({"success": False, "error": "Cannot delete admin"}), 403

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    # Delete user's messages
    Message.query.filter_by(user=username).delete()
    # Delete user
    db.session.delete(user)
    db.session.commit()

    return jsonify({"success": True})

# Admin: delete all messages
@app.route('/admin/delete_all_messages', methods=['POST'])
def delete_all_messages():
    data = request.json
    admin_username = data.get("admin_username")
    admin_password = data.get("admin_password")

    if admin_username != ADMIN_USERNAME or admin_password != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    num_deleted = Message.query.delete()
    db.session.commit()

    return jsonify({"success": True, "deleted_messages": num_deleted})

if __name__ == '__main__':
    app.run(debug=True)
