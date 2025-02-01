import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import random

randomport = 999

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

# Directory for storing user sessions
SESSIONS_DIR = "sessions"

if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)


def get_session_file(uid):
    """Returns the file path for a user's session."""
    return os.path.join(SESSIONS_DIR, f"user_{uid}.json")


def load_session(uid):
    """Loads a user's session from their dedicated file, or creates a new one if not found."""
    session_file = get_session_file(uid)
    if os.path.exists(session_file):
        try:
            with open(session_file, "r") as f:
                data = json.load(f)
                history = data.get("history", [])
                
                # Rebuild the history to match the expected format
                rebuilt_history = []
                for entry in history:
                    # Check if 'parts' is missing or has no content
                    if 'parts' not in entry or len(entry['parts']) == 0:
                        rebuilt_history.append(
                            {
                                "role": entry.get("role", "user"),  # Default to 'user' if missing
                                "parts": [{"text": entry.get("text", "")}]  # Ensure there's a 'text' field
                            }
                        )
                    else:
                        rebuilt_history.append(
                            {
                                "role": entry.get("role", "user"),
                                "parts": entry["parts"]
                            }
                        )
                return model.start_chat(history=rebuilt_history)
        except json.JSONDecodeError:
            print(f"[ERROR] Corrupted JSON file for user {uid}. Resetting.")
            return model.start_chat(history=[])
    
    return model.start_chat(history=[])  # Default empty session


    
    return model.start_chat(history=[])  # Default empty session

def save_session(uid, chat_session):
    """Saves a user's chat session to their dedicated file."""
    session_file = get_session_file(uid)
    
    # Debugging: print the history structure to understand its format
    print(f"[DBG] Chat history structure for user {uid}: {chat_session.history}")
    
    session_data = {
        "history": [
            {
                "parts": [{"text": msg.parts[0].text}],  # Wrap the message text in 'parts'
                "role": msg.role  # Use the 'role' from the message
            }
            for msg in chat_session.history
        ]
    }
    
    with open(session_file, "w") as f:
        json.dump(session_data, f, indent=4)


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

    # Load or create a chat session for the user
    chat_session = load_session(userid)

    print(f"[DBG] Processing query for user {userid}")

    # Send the query to the generative model
    response = chat_session.send_message(query).text

    # Save the updated session
    save_session(userid, chat_session)

    return jsonify({"response": response})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=randomport)
