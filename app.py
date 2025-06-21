from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # allow all origins for testing

app = Flask(__name__)
CORS(app)

# SQLite config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///messages_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Admin credentials in plain text
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Pusheen#99"

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # store plain text (insecure!)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(80), nullable=False)
    text = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()

# Register new user (store plain text password)
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

# Login user/admin (plain-text check)
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

# Other routes unchanged...

if __name__ == '__main__':
    app.run(debug=True)
