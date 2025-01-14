"""Master agent that coordinates other specialized agents."""

from typing import Optional, Dict, Any
import json
import asyncio
from pathlib import Path
import os

from config.settings import (
    AGENT_SETTINGS,
    PERSONALITY_SETTINGS,
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

class MasterAgent(BaseAgent):
    """Master agent that coordinates other specialized agents."""
    
    def __init__(self):
        """Initialize the master agent."""
        super().__init__(
            agent_type="master",
            system_prompt="""I am a master agent that coordinates multiple specialized agents to help users.
I analyze requests and route them to the appropriate specialized agent:
- Vision agent for image analysis and screenshots
- Memory agent for conversation history
- Search agent for information lookup
- Writer agent for text generation
- Code agent for programming help
- Scanner agent for document processing
- Location agent for location-based tasks
- Learning agent for educational content

I ensure each request is handled by the most appropriate agent."""
        )
        
        # Copy personality settings
        self.personality = PERSONALITY_SETTINGS.copy()
        
        # Initialize enabled agents
        self.agents = {}
        if is_agent_enabled("memory"):
            self.agents["memory"] = MemoryAgent()
        if is_agent_enabled("search"):
            self.agents["search"] = SearchAgent()
        if is_agent_enabled("writer"):
            self.agents["writer"] = WriterAgent()
        if is_agent_enabled("code"):
            self.agents["code"] = CodeAgent()
        if is_agent_enabled("scanner"):
            self.agents["scanner"] = ScannerAgent()
        if is_agent_enabled("vision"):
            self.agents["vision"] = VisionAgent()
        if is_agent_enabled("location"):
            self.agents["location"] = LocationAgent()
        if is_agent_enabled("learning"):
            self.agents["learning"] = LearningAgent()
            
        print("✓ Master agent initialized with enabled agents")

    async def process(self, query: str) -> str:
        """Process a user query and return a response."""
        print(f"\nProcessing query: {query}")
        
        try:
            # Process query with enabled agents
            response = await self._process_with_agents(query)
            return response
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(error_msg)
            return error_msg

    async def _process_with_agents(self, query: str) -> str:
        """Process a query using available agents."""
        print("\n=== Master Agent Processing ===")
        print(f"Query: {query}")
        
        try:
            # Check if this is an image analysis request
            if query.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                if os.path.exists(query):
                    if "vision" in self.agents:
                        print("Routing to vision agent for image analysis")
                        return await self.agents["vision"].analyze_image(query)
                    else:
                        return "Vision agent is not enabled. Cannot analyze images."
                else:
                    return f"Image file not found: {query}"
                    
            # First check for file paths in the query
            words = query.split()
            file_path = None
            for word in words:
                # Remove quotes from the path if present
                word = word.strip("'\"")
                if os.path.exists(word):
                    file_path = word
                    print(f"Found file path: {file_path}")
                    break
            
            if file_path:
                print(f"Processing file: {file_path}")
                file_ext = os.path.splitext(file_path)[1].lower()
                print(f"File extension: {file_ext}")
                
                # Image files for vision agent
                if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                    if "vision" in self.agents:
                        print(f"Routing to vision agent")
                        analysis_query = query.replace(file_path, '').replace("'", "").replace('"', '').strip()
                        print(f"Analysis query: {analysis_query}")
                        return await self.agents["vision"].analyze_image(file_path, analysis_query)
                    else:
                        return "Vision agent is not available for image analysis."
                
                # Document files for scanner agent
                elif file_ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt']:
                    if "scanner" in self.agents:
                        print(f"Routing to scanner agent")
                        analysis_query = query.replace(file_path, '').replace("'", "").replace('"', '').strip()
                        print(f"Analysis query: {analysis_query}")
                        return await self.agents["scanner"].process_document(file_path, analysis_query)
                    else:
                        return "Scanner agent is not available for document analysis."
                
                else:
                    return f"Unsupported file type: {file_ext}. I can analyze images (.jpg, .png, etc.) and documents (.pdf, .doc, etc.)"
            
            # Check for screenshot request
            if "screenshot" in query.lower():
                if "vision" in self.agents:
                    print("Taking and analyzing screenshot")
                    return await self.agents["vision"].capture_screen()
                else:
                    return "Vision agent is not available for screenshots."

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

            # Handle other agent processing...
            print("No specialized handling needed, processing as regular query")
            response = await super().process(query)
            return response
            
        except Exception as e:
            error_msg = f"Error in agent processing: {str(e)}"
            print(error_msg)
            return error_msg

# Initialize the master agent
master_agent = MasterAgent() 