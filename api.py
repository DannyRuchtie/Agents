from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os

# --- Assumption: MasterAgent is in an 'agents' directory ---
# Ensure this path is correct relative to where you run this FastAPI app.
try:
    from agents.master_agent import MasterAgent
    # If MasterAgent's __init__ or other parts need async setup, that needs to be handled.
    # For now, assuming synchronous instantiation and async process method.
except ImportError:
    print("ERROR: Could not import MasterAgent. Please ensure 'agents.master_agent' is correct.")
    print("Using a DUMMY MasterAgent for now to allow the API to start.")
    # Fallback DUMMY MasterAgent if the real one is not found
    class MasterAgent:
        def __init__(self):
            print("DUMMY MasterAgent initialized.")
        async def process(self, message: str) -> str:
            print(f"DUMMY MasterAgent received: {message}")
            return f"This is a dummy MasterAgent response to: {message}"

app = FastAPI(
    title="Master Agent API",
    description="API to interact with the MasterAgent for processing messages.",
    version="1.0.0"
)

# --- MasterAgent Instance ---
# Initialize MasterAgent. If it has complex async setup,
# FastAPI's lifespan events (startup/shutdown) might be needed.
# For now, a simple instantiation.
master_agent_instance = MasterAgent()

# --- Pydantic Models for Request and Response ---
class ProcessMessageRequest(BaseModel):
    message: str

class ProcessMessageResponse(BaseModel):
    response: str

# --- API Endpoints ---
@app.post("/process-message", response_model=ProcessMessageResponse)
async def process_message_endpoint(request: ProcessMessageRequest):
    """
    Receives a user message, processes it with MasterAgent, 
    and returns the agent's response.
    """
    if not request.message:
        raise HTTPException(status_code=400, detail="Missing 'message' in request body")

    print(f"[FastAPI /process-message] Received message: '{request.message}'")
    try:
        # Assuming MasterAgent.process is an async method as in the original Flask app
        agent_response = await master_agent_instance.process(request.message)
        print(f"[FastAPI /process-message] MasterAgent responded: '{agent_response}'")
        return ProcessMessageResponse(response=agent_response)
    except Exception as e:
        # Log the full error for debugging on the server
        print(f"[FastAPI ERROR] Error processing message with MasterAgent: {str(e)}")
        # Consider logging the full traceback here in a real application
        # import traceback
        # print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing message with MasterAgent: {str(e)}")

@app.get("/status")
async def get_status():
    """Basic status endpoint to check if the API is running."""
    return {"status": "Master Agent API is running"}

# --- How to Run This FastAPI Application (on Machine A) ---
# 1. Save this file as `api.py` (or your preferred name for the API server).
# 2. Ensure you have `fastapi` and `uvicorn` installed:
#    `pip install fastapi "uvicorn[standard]"`
# 3. Run from your terminal (in the directory containing this file):
#    `uvicorn api:app --host 0.0.0.0 --port 5001 --reload`
#    Replace `api` with the Python filename if you named it differently.
#    The `--host 0.0.0.0` makes it accessible on your network.
#    The `--port 5001` is an example; use any available port.
#    The `--reload` flag is useful for development as it restarts the server on code changes.

if __name__ == "__main__":
    # This block allows running with `python api.py` for simple testing,
    # but `uvicorn` is recommended for production or more control.
    print("Attempting to run with Uvicorn directly. For production, use the uvicorn command.")
    uvicorn.run(app, host="0.0.0.0", port=5001) 