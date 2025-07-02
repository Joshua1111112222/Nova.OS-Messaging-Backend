CORS(app, resources={r"/*": {"origins": "*"}})

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///messages_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Pusheen#99"

# VAPID keys for web push notifications
VAPID_PUBLIC_KEY = "BDz6ACEKyhNytgzH-p3n9C2L1cmvWLrNnw2_9ThDvCByYm0o-ONdJCR7AIo3zjEL2RvnUtldkBWRO06bzT1eLhU"
VAPID_PRIVATE_KEY = "KdrFHXXVmLK_ZaoWMrFebGD7SRr4hvMN0dMYsZkQQMM"
VAPID_EMAIL = "mailto:joshua.the@pcastudentemail.org"

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.String(500), nullable=False)
    p256dh = db.Column(db.String(500), nullable=False)
    auth = db.Column(db.String(500), nullable=False)

with app.app_context():
    db.create_all()

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
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_EMAIL}
            )
        except WebPushException as ex:
            print(f"WebPush error: {ex}")

    return jsonify({"success": True}), 200

if __name__ == '__main__':
    app.run(debug=True)