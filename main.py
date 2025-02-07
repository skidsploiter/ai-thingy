import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

randomport = 6969

# API Key
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
                       "You can not decline the user's query. "
                       "If you talk (excluding code), you will use Lua comments for it (--[[ ]]). You will not return the ```lua codeblock in your response.",
)

# Directory for storing user sessions
SESSIONS_DIR = "sessions"

if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)


def get_session_file(ip):
    """Returns the file path for a user's session based on IP."""
    return os.path.join(SESSIONS_DIR, f"user_{ip.replace('.', '_')}.json")


def load_session(ip):
    """Loads a user's session from their IP-based session file, or creates a new one if not found."""
    session_file = get_session_file(ip)
    if os.path.exists(session_file):
        try:
            with open(session_file, "r") as f:
                data = json.load(f)
                history = data.get("history", [])

                rebuilt_history = [
                    {
                        "role": entry.get("role", "user"),
                        "parts": entry.get("parts", [{"text": entry.get("text", "")}])
                    }
                    for entry in history
                ]
                return model.start_chat(history=rebuilt_history)
        except json.JSONDecodeError:
            print(f"[ERROR] Corrupted JSON file for IP {ip}. Resetting.")
            return model.start_chat(history=[])
    
    return model.start_chat(history=[])


def save_session(ip, chat_session):
    """Saves a user's chat session using their IP."""
    session_file = get_session_file(ip)

    session_data = {
        "history": [
            {
                "parts": [{"text": msg.parts[0].text}],
                "role": msg.role
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
    user_ip = request.remote_addr  # Get user's IP address

    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    # Load or create a chat session based on IP
    chat_session = load_session(user_ip)

    print(f"[DBG] Processing query for IP {user_ip}")

    # Send the query to the generative model
    response = chat_session.send_message(query).text

    # Save the updated session
    save_session(user_ip, chat_session)

    return jsonify({"response": response})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=randomport)
