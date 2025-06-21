from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory storage for messages (use a database for production)
messages = []

@app.route('/messages', methods=['GET'])
def get_messages():
    """Endpoint to retrieve all messages."""
    return jsonify(messages)

@app.route('/messages', methods=['POST'])
def send_message():
    """Endpoint to send a new message."""
    data = request.json
    if 'text' in data and 'sent' in data:
        messages.append(data)
        return jsonify({"success": True, "message": "Message sent!"}), 201
    return jsonify({"success": False, "error": "Invalid message format"}), 400

if __name__ == '__main__':
    app.run(debug=True)