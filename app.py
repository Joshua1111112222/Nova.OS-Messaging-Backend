from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import json
from pywebpush import webpush, WebPushException

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///messages_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Pusheen#99"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(80), nullable=False)
    text = db.Column(db.Text, nullable=False)

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.String(500), nullable=False)
    p256dh = db.Column(db.String(500), nullable=False)
    auth = db.Column(db.String(500), nullable=False)

with app.app_context():
    db.create_all()

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
    return jsonify({"success": True})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return jsonify({"success": True, "admin": True, "username": ADMIN_USERNAME})
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        return jsonify({"success": True, "admin": False, "username": username})
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/messages', methods=['GET', 'POST'])
def messages():
    if request.method == 'GET':
        return jsonify([{"id": m.id, "user": m.user, "text": m.text} for m in Message.query.all()])
    data = request.json
    user, text = data.get("user"), data.get("text")
    if not user or not text:
        return jsonify({"success": False, "error": "Missing user or text"}), 400
    msg = Message(user=user, text=text)
    db.session.add(msg)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/edit_message', methods=['POST'])
def edit_message():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    message_id = data.get("message_id")
    new_text = data.get("new_text")
    msg = Message.query.get(message_id)
    if not msg:
        return jsonify({"success": False, "error": "Message not found"}), 404
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        msg.text = new_text
    else:
        user = User.query.filter_by(username=username, password=password).first()
        if not user or msg.user != username:
            return jsonify({"success": False, "error": "Not authorized"}), 403
        msg.text = new_text
    db.session.commit()
    return jsonify({"success": True})

@app.route('/admin/delete_message', methods=['POST'])
def delete_message():
    data = request.json
    if data.get("admin_username") != ADMIN_USERNAME or data.get("admin_password") != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    msg = Message.query.get(data.get("message_id"))
    if not msg:
        return jsonify({"success": False, "error": "Message not found"}), 404
    db.session.delete(msg)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/admin/list_users')
def list_users():
    if request.args.get("admin_username") != ADMIN_USERNAME or request.args.get("admin_password") != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    return jsonify([u.username for u in User.query.all()])

@app.route('/admin/delete_user', methods=['POST'])
def delete_user():
    data = request.json
    if data.get("admin_username") != ADMIN_USERNAME or data.get("admin_password") != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    username = data.get("username")
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    db.session.delete(user)
    Message.query.filter_by(user=username).delete()
    db.session.commit()
    return jsonify({"success": True})

@app.route('/admin/delete_all_messages', methods=['POST'])
def delete_all_messages():
    data = request.json
    if data.get("admin_username") != ADMIN_USERNAME or data.get("admin_password") != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    Message.query.delete()
    db.session.commit()
    return jsonify({"success": True})

@app.route('/admin/view_passwords', methods=['GET'])
def view_passwords():
    """Admin can view all users and their passwords."""
    if request.args.get("admin_username") != ADMIN_USERNAME or request.args.get("admin_password") != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    users = [{"username": u.username, "password": u.password} for u in User.query.all()]
    return jsonify(users)

@app.route('/admin/change_password', methods=['POST'])
def change_password():
    """Admin can change a user's password."""
    data = request.json
    if data.get("admin_username") != ADMIN_USERNAME or data.get("admin_password") != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    username = data.get("username")
    new_password = data.get("new_password")
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    user.password = new_password
    db.session.commit()
    return jsonify({"success": True, "message": f"Password for {username} updated"})

@app.route('/subscribe', methods=['POST'])
def subscribe():
    data = request.json
    subscription = Subscription(
        endpoint=data['endpoint'],
        p256dh=data['keys']['p256dh'],
        auth=data['keys']['auth']
    )
    db.session.add(subscription)
    db.session.commit()
    return jsonify({"success": True}), 201

@app.route('/send-notification', methods=['POST'])
def send_notification():
    data = request.json
    title = data.get("title", "New Message")
    body = data.get("body", "You have a new message!")
    subscriptions = Subscription.query.all()

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth
                    }
                },
                data=json.dumps({"title": title, "body": body}),
                vapid_private_key="KdrFHXXVmLK_ZaoWMrFebGD7SRr4hvMN0dMYsZkQQMM",
                vapid_claims={"sub": "mailto:joshua.the@pcastudentemail.org"}
            )
        except WebPushException as ex:
            print(f"WebPush error: {ex}")

    return jsonify({"success": True}), 200

if __name__ == '__main__':
    app.run(debug=True)