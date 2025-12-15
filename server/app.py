import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import uuid
from datetime import datetime

load_dotenv()

from agent import process_message

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

conversations = {}

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route("/api/chat", methods=["POST"])
def chat():
    """Process a chat message and return the AI response."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        user_message = data.get("message", "").strip()
        conversation_id = data.get("conversationId")
        user_id = data.get("userId", "default-user")
        
        if not user_message:
            return jsonify({"error": "Message is required"}), 400
        
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            conversations[conversation_id] = {
                "id": conversation_id,
                "userId": user_id,
                "messages": [],
                "createdAt": datetime.now().isoformat(),
                "updatedAt": datetime.now().isoformat()
            }
        
        conversation = conversations.get(conversation_id, {
            "id": conversation_id,
            "userId": user_id,
            "messages": [],
            "createdAt": datetime.now().isoformat(),
            "updatedAt": datetime.now().isoformat()
        })
        
        conversation_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in conversation.get("messages", [])
        ]
        
        result = process_message(
            user_message=user_message,
            user_id=user_id,
            conversation_history=conversation_history
        )
        
        response_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": result["content"],
            "timestamp": datetime.now().isoformat(),
            "flightResults": result.get("flight_results", []),
            "memoryContext": result.get("memory_context")
        }
        
        conversation["messages"].append({
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        conversation["messages"].append(response_message)
        conversation["updatedAt"] = datetime.now().isoformat()
        conversations[conversation_id] = conversation
        
        return jsonify({
            "message": response_message,
            "conversationId": conversation_id
        })
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            "error": str(e),
            "message": {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": f"I apologize, but I encountered an error: {str(e)}. Please try again.",
                "timestamp": datetime.now().isoformat(),
                "flightResults": []
            },
            "conversationId": data.get("conversationId", str(uuid.uuid4()))
        }), 500

@app.route("/api/conversations/<conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    """Get a conversation by ID."""
    conversation = conversations.get(conversation_id)
    
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    return jsonify(conversation)

@app.route("/api/conversations", methods=["GET"])
def list_conversations():
    """List all conversations for a user."""
    user_id = request.args.get("userId", "default-user")
    
    user_conversations = [
        conv for conv in conversations.values()
        if conv.get("userId") == user_id
    ]
    
    return jsonify(user_conversations)

if __name__ == "__main__":
    port = int(os.environ.get("PYTHON_BACKEND_PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
