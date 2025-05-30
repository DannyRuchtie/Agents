from flask import Flask, request, jsonify
import os
from pathlib import Path
from dotenv import load_dotenv

# from agents.master_agent import MasterAgent # We'll uncomment and use this soon
# from config.paths_config import ensure_directories # We might need this
# from config.settings import debug_print # For consistency in debugging

app = Flask(__name__)

# --- Configuration Loading ---
def load_app_config():
    """Loads .env configuration."""
    # Construct an absolute path to the .env file relative to this script's location
    # Assuming api.py is in the project root, same as main.py where .env is expected
    script_dir = Path(__file__).resolve().parent
    env_path = script_dir / ".env"
    
    print(f"[API_DEBUG] Attempting to load .env file from: {env_path}")
    loaded_successfully = load_dotenv(dotenv_path=env_path, override=True, verbose=True)
    print(f"[API_DEBUG] load_dotenv successful: {loaded_successfully}")
    
    # ensure_directories() # Call this if your agents create files/logs

load_app_config()
# master_agent_instance = MasterAgent() # Initialize once if appropriate, or per request

@app.route('/chat', methods=['POST'])
async def chat():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "Missing 'message' in request body"}), 400

    user_message = data['message']
    
    # ---- Placeholder for MasterAgent integration ----
    # print(f"[API_DEBUG] Received message: {user_message}")
    # # For now, we'll just echo. Later, this will call master_agent.process()
    # # response_from_agent = await master_agent_instance.process(user_message)
    # response_from_agent = f"API received: {user_message}" # Replace with actual agent call
    # print(f"[API_DEBUG] Response from agent: {response_from_agent}")
    # return jsonify({"response": response_from_agent})
    # ---- End Placeholder ----

    # For now, let's just simulate a response until MasterAgent is fully integrated
    # This part will be replaced by the actual call to MasterAgent
    print(f"[API_DEBUG] Received message for API: {user_message}")
    
    # Simulate agent processing for now.
    # We will need to properly integrate the async MasterAgent.process call.
    # Flask by default is not async for route handlers, so we'll need to address that.
    # For a quick start, let's assume MasterAgent can be called in a blocking way for now,
    # or we use `asyncio.run()` if `MasterAgent.process` is async.
    
    # This is a temporary synchronous placeholder.
    # We'll need to correctly call the async `master_agent.process`
    try:
        # ---- TEMPORARY: Direct MasterAgent Usage ----
        # This is a simplified integration. Proper async handling with Flask needs care.
        from agents.master_agent import MasterAgent # Local import for now
        # from config.paths_config import ensure_directories
        # ensure_directories() # Ensure this is called

        # Each request could get a new agent, or use a shared one (consider thread-safety/state)
        current_master_agent = MasterAgent()
        # The MasterAgent.process is async, Flask routes are sync by default.
        # We need to run the async function in an event loop.
        # A simple way for now, but for production, consider an ASGI server like Uvicorn with Flask.
        import asyncio
        agent_response = await current_master_agent.process(user_message)
        
        print(f"[API_DEBUG] MasterAgent response: {agent_response}")
        return jsonify({"response": agent_response})
    except Exception as e:
        print(f"[API_ERROR] Error processing message with MasterAgent: {str(e)}")
        return jsonify({"error": f"Error processing message: {str(e)}"}), 500

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "API is running"}), 200

if __name__ == '__main__':
    # Ensure Flask runs on an accessible IP (0.0.0.0) and a chosen port
    # Debug mode is useful for development
    app.run(host='0.0.0.0', port=5001, debug=True) 