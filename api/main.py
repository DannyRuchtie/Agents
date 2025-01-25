"""FastAPI application for the Agents system."""
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.master_agent import MasterAgent
from config.settings import VOICE_SETTINGS, get_agent_status

# Initialize FastAPI app
app = FastAPI(
    title="Agents API",
    description="API interface for the Agents system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize master agent
master_agent = MasterAgent()

class QueryRequest(BaseModel):
    """Request model for queries."""
    query: str
    context: Optional[Dict[str, Any]] = None

class AgentRequest(BaseModel):
    """Request model for agent operations."""
    agent_name: str
    action: str  # enable/disable
    
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "status": "ok",
        "message": "Agents API is running",
        "version": "1.0.0"
    }

@app.get("/agents")
async def list_agents():
    """List all available agents and their status."""
    try:
        # Get agent status from settings
        agent_status = get_agent_status()
        
        # Create a serializable response
        agents_info = {}
        for name, agent in master_agent.agents.items():
            agents_info[name] = {
                "type": agent.agent_type,
                "enabled": agent_status.get(name, False)
            }
            
        return {
            "agents": agents_info,
            "total": len(agents_info)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def process_query(request: QueryRequest):
    """Process a query using the master agent."""
    try:
        response = await master_agent.process(request.query)
        return {
            "status": "success",
            "query": request.query,
            "response": response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agents/{agent_name}/{action}")
async def manage_agent(agent_name: str, action: str):
    """Enable or disable an agent."""
    if action not in ["enable", "disable"]:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'enable' or 'disable'")
        
    try:
        if action == "enable":
            master_agent.enable_agent(agent_name)
        else:
            master_agent.disable_agent(agent_name)
            
        return {
            "status": "success",
            "message": f"Agent {agent_name} {action}d successfully",
            "agent": agent_name,
            "action": action
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/voice/status")
async def get_voice_status():
    """Get voice output status."""
    try:
        return {
            "status": "success",
            "voice_enabled": VOICE_SETTINGS["enabled"],
            "current_voice": VOICE_SETTINGS["voice"],
            "speed": VOICE_SETTINGS["speed"],
            "available_voices": VOICE_SETTINGS["available_voices"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice/{action}")
async def manage_voice(action: str):
    """Manage voice output settings."""
    valid_actions = ["enable", "disable", "stop"]
    if action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Use one of: {valid_actions}")
        
    try:
        if action == "stop":
            # Stop current speech if any
            from utils.voice import voice_output
            voice_output.stop_speaking()
        else:
            # Update voice settings
            VOICE_SETTINGS["enabled"] = (action == "enable")
            
        return {
            "status": "success",
            "message": f"Voice {action}d successfully",
            "action": action
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 