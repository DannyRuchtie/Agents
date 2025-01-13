"""Master agent that coordinates other specialized agents."""

from typing import Optional, Dict, Any
import json
import asyncio
from pathlib import Path

from config.settings import (
    AGENT_SETTINGS,
    PERSONALITY_SETTINGS,
    VOICE_SETTINGS,
    SYSTEM_SETTINGS,
    is_agent_enabled,
    enable_agent,
    disable_agent,
    is_debug_mode,
    debug_print
)

from agents.base_agent import BaseAgent
from agents.memory_agent import MemoryAgent
from agents.search_agent import SearchAgent
from agents.writer_agent import WriterAgent
from agents.code_agent import CodeAgent
from agents.scanner_agent import ScannerAgent
from agents.vision_agent import VisionAgent
from agents.location_agent import LocationAgent
from agents.learning_agent import LearningAgent
from agents.voice import voice_output

class MasterAgent(BaseAgent):
    """Master agent that coordinates other specialized agents."""
    
    def __init__(self):
        """Initialize the master agent."""
        super().__init__()
        
        # Copy personality settings
        self.personality = PERSONALITY_SETTINGS.copy()
        
        # Initialize enabled agents
        self.agents = {}
        if is_agent_enabled("memory_agent"):
            self.agents["memory"] = MemoryAgent()
        if is_agent_enabled("search_agent"):
            self.agents["search"] = SearchAgent()
        if is_agent_enabled("writer_agent"):
            self.agents["writer"] = WriterAgent()
        if is_agent_enabled("code_agent"):
            self.agents["code"] = CodeAgent()
        if is_agent_enabled("scanner_agent"):
            self.agents["scanner"] = ScannerAgent()
        if is_agent_enabled("vision_agent"):
            self.agents["vision"] = VisionAgent()
        if is_agent_enabled("location_agent"):
            self.agents["location"] = LocationAgent()
        if is_agent_enabled("learning_agent"):
            self.agents["learning"] = LearningAgent()
            
        debug_print("✓ Master agent initialized with enabled agents")
        
    async def process(self, query: str) -> str:
        """Process a user query and return a response."""
        debug_print(f"\nProcessing query: {query}")
        
        try:
            # Handle voice commands
            if query.lower().startswith(("voice", "speak")):
                parts = query.lower().split()
                if len(parts) >= 2:
                    cmd = parts[1]
                    
                    if cmd == "status":
                        status = "enabled" if VOICE_SETTINGS["enabled"] else "disabled"
                        voice = VOICE_SETTINGS["voice"]
                        speed = VOICE_SETTINGS["speed"]
                        return f"Voice output is {status}, using voice '{voice}' at speed {speed}x"
                        
                    elif cmd in ["on", "enable"]:
                        VOICE_SETTINGS["enabled"] = True
                        return "Voice output enabled"
                        
                    elif cmd in ["off", "disable"]:
                        VOICE_SETTINGS["enabled"] = False
                        return "Voice output disabled"
                        
                    elif cmd == "voice" and len(parts) >= 3:
                        voice = parts[2]
                        if voice in VOICE_SETTINGS["available_voices"]:
                            VOICE_SETTINGS["voice"] = voice
                            return f"Voice set to '{voice}'"
                        else:
                            return f"Invalid voice. Available voices: {', '.join(VOICE_SETTINGS['available_voices'].keys())}"
                            
                    elif cmd == "speed" and len(parts) >= 3:
                        try:
                            speed = float(parts[2])
                            if 0.5 <= speed <= 2.0:
                                VOICE_SETTINGS["speed"] = speed
                                return f"Voice speed set to {speed}x"
                            else:
                                return "Speed must be between 0.5 and 2.0"
                        except ValueError:
                            return "Invalid speed value"
            
            # Process query with enabled agents
            response = await self._process_with_agents(query)
            
            # Speak response if voice is enabled
            if VOICE_SETTINGS["enabled"]:
                debug_print("Speaking response with voice output")
                voice_output.speak(response)
                
            return response
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            debug_print(error_msg)
            return error_msg
            
    async def _process_with_agents(self, query: str) -> str:
        """Process query using available agents."""
        # Implementation of agent coordination logic
        # This is a placeholder - implement actual agent coordination
        return f"Processing: {query}"

# Initialize the master agent
master_agent = MasterAgent() 