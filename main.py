import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

# API Key (Replace with a secure method to load it)
key = "AIzaSyAIPd5kfMbZs1xUg6E6C_gShaRyeluM_kI"

# Debugging information
print("[DBG] Imported modules")
print("[DBG] Using gemini key " + key)
genai.configure(api_key=key)

# Create the model configuration
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# Initialize the generative model
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config=generation_config,
    system_instruction="You are a lua code generator who only makes localscripts. "
                       "You do not use markdown and only return code if code is asked, "
                       "else continue talking. You are not allowed to use any other language than lua. "
                       "You can not decline the user's query.",
)

# Path to the JSON file where session data will be saved
SESSION_FILE = 'user_sessions.json'


# Load user sessions from the JSON file
def load_sessions():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                data = json.load(f)

                # Reconstruct ChatSessions
                return {
                    uid: model.start_chat(history=session_data["history"])
                    for uid, session_data in data.items()
                }
        except (json.JSONDecodeError, KeyError):
            print("[ERROR] Corrupted JSON file. Resetting user_sessions.json.")
            return {}  # Return an empty dictionary if the file is corrupted

    return {}  # Return an empty dictionary if the file does not exist


# Save user sessions to the JSON file
def save_sessions(sessions):
    json_safe_sessions = {
        uid: {"history": chat_session.history}  # Store only history, not the ChatSession object
        for uid, chat_session in sessions.items()
    }

    with open(SESSION_FILE, 'w') as f:
        json.dump(json_safe_sessions, f, indent=4)


# Dictionary to store chat histories for each user (loaded from JSON)
user_sessions = load_sessions()

# Flask app setup
app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    return 'Chaos AI API'


@app.route('/api/ai', methods=['GET'])
def ai_query():
    query = request.args.get('query')
    userid = request.args.get('uid')

    if not query or not userid:
        return jsonify({"error": "Both query and uid are required."}), 400

    # Create a new chat session if it doesn't exist for the user
    if userid not in user_sessions:
        user_sessions[userid] = model.start_chat(history=[])
        print(f"[DBG] Created new chat session for user {userid}")

    # Send the query to the generative model
    chat_session = user_sessions[userid]
    response = chat_session.send_message(query).text

    # Save the updated sessions to the JSON file after each query
    save_sessions(user_sessions)

    return jsonify({"response": response})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1727)
