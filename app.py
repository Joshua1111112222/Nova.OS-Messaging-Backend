from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from pywebpush import webpush, WebPushException
from bs4 import BeautifulSoup
import google.generativeai as genai
import requests
import json

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///messages_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Pusheen#99"

# VAPID Keys for push notifications
VAPID_PUBLIC_KEY = "BOnz0DjCCHAcB6oFJ4uE_w6YomqD4pywL-lKISysBN9_puPG8Ybb5T1ZyCxlbXZJcF0VhkAfKPXh59mnGCLeNGk"
VAPID_PRIVATE_KEY = "AhdKoxKeSoMaC1-DCu7Yp3u5sl5UxxZ9PtxomOVPplY"

# Gemini API key for AI chat
genai.configure(api_key="YOUR_GEMINI_API_KEY_HERE")

SYSTEM_PROMPT = (
    "You are an AI named Delta, created by Joshua The. "
    "Your mission is to follow what the user tells you to your extent and to be helpful and never harmful."
)

# DB Models

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

# Helper: Web search snippets for fallback context
def web_search_snippets(query, max_snippets=3):
    try:
        search_url = f"https://www.google.com/search?q={'+'.join(query.split())}"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(search_url, headers=headers, timeout=5)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        snippets = []
        for div in soup.find_all("div", class_="BNeawe s3v9rd AP7Wnd"):
            text = div.get_text(strip=True)
            if text and text not in snippets:
                snippets.append(text)
            if len(snippets) >= max_snippets:
                break
        return " ".join(snippets)
    except Exception as e:
        print(f"Web search error: {e}")
        return ""

# User registration
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username, password = data.get("username"), data.get("password")
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    if username == ADMIN_USERNAME:
        return jsonify({"success": False, "error": "Cannot register as admin"}), 403
    if User.query.filter_by(username=username).first():
        return jsonify({"success": False, "error": "Username taken"}), 409
    db.session.add(User(username=username, password=password))
    db.session.commit()
    return jsonify({"success": True})

# User login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username, password = data.get("username"), data.get("password")
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return jsonify({"success": True, "admin": True, "username": ADMIN_USERNAME})
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        return jsonify({"success": True, "admin": False, "username": username})
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

# Get or post messages
@app.route('/messages', methods=['GET', 'POST'])
def messages():
    if request.method == 'GET':
        all_msgs = [{"id": m.id, "user": m.user, "text": m.text} for m in Message.query.all()]
        return jsonify(all_msgs)
    data = request.json
    user, text = data.get("user"), data.get("text")
    if not user or not text:
        return jsonify({"success": False, "error": "Missing user or text"}), 400
    db.session.add(Message(user=user, text=text))
    db.session.commit()
    return jsonify({"success": True})

# Edit message (admin or own message)
@app.route('/edit_message', methods=['POST'])
def edit_message():
    data = request.json
    username, password = data.get("username"), data.get("password")
    message_id, new_text = data.get("message_id"), data.get("new_text")
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

# Delete message (admin only)
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

# List users (admin only)
@app.route('/admin/list_users')
def list_users():
    if request.args.get("admin_username") != ADMIN_USERNAME or request.args.get("admin_password") != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    return jsonify([u.username for u in User.query.all()])

# Delete user (admin only)
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

# Delete all messages (admin only)
@app.route('/admin/delete_all_messages', methods=['POST'])
def delete_all_messages():
    data = request.json
    if data.get("admin_username") != ADMIN_USERNAME or data.get("admin_password") != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    Message.query.delete()
    db.session.commit()
    return jsonify({"success": True})

# View passwords (admin only)
@app.route('/admin/view_passwords', methods=['GET'])
def view_passwords():
    if request.args.get("admin_username") != ADMIN_USERNAME or request.args.get("admin_password") != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    users = [{"username": u.username, "password": u.password} for u in User.query.all()]
    return jsonify(users)

# Change password (admin only)
@app.route('/admin/change_password', methods=['POST'])
def change_password():
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

# Push notification subscription
@app.route('/subscribe', methods=['POST'])
def subscribe():
    data = request.json
    sub = Subscription(
        endpoint=data['endpoint'],
        p256dh=data['keys']['p256dh'],
        auth=data['keys']['auth']
    )
    db.session.add(sub)
    db.session.commit()
    return jsonify({"success": True}), 201

# Send push notification to all subscribers
@app.route('/send-notification', methods=['POST'])
def send_notification():
    data = request.json
    title = data.get("title", "New Message")
    body = data.get("body", "You have a new message!")
    for sub in Subscription.query.all():
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=json.dumps({"title": title, "body": body}),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": "mailto:joshuathe2011@gmail.com"},
                vapid_public_key=VAPID_PUBLIC_KEY,
            )
        except WebPushException as ex:
            print(f"WebPush failed: {ex}")
    return jsonify({"success": True}), 200

# AI chat endpoint with Gemini + fallback
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(force=True)
    prompt = data.get("prompt", "").strip()
    history = data.get("history", [])

    if not prompt:
        return jsonify({"success": False, "error": "Prompt is required"}), 400
    if not isinstance(history, list):
        return jsonify({"success": False, "error": "History must be a list"}), 400

    messages_for_gemini = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        role = msg.get("role")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages_for_gemini.append({"role": role, "content": content})
    messages_for_gemini.append({"role": "user", "content": prompt})

    try:
        model = genai.GenerativeModel("chat-bison-001")

        response = model.generate_chat(
            messages=messages_for_gemini,
            temperature=0.7,
            candidate_count=1,
        )
        answer = response.text.strip()

        # fallback on generic/empty answers
        if (
            not answer
            or len(answer) < 5
            or any(phrase in answer.lower() for phrase in ["i don't know", "as an ai", "sorry", "unable"])
        ):
            snippets = web_search_snippets(prompt)
            if snippets:
                messages_for_gemini.append({"role": "system", "content": f"Additional context from web search: {snippets}"})
                response = model.generate_chat(messages=messages_for_gemini)
                answer = response.text.strip()

    except Exception as e:
        print(f"Gemini API error: {e}")
        return jsonify({"success": False, "error": "Error processing AI response"}), 500

    return jsonify({"success": True, "answer": answer})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
