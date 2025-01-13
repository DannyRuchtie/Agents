"""Master agent that coordinates other specialized agents."""

from typing import Optional
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
    get_agent_status,
    get_agent_info,
    save_settings,
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
from utils.voice import voice_output

MASTER_SYSTEM_PROMPT = """You are a highly capable AI coordinator running on macOS, with access to a team of specialized expert agents. Think of yourself as an executive assistant who can delegate tasks to the perfect expert for each job.

IMPORTANT: Keep your responses concise and to the point - ideally 2-3 sentences maximum. Avoid lengthy explanations unless specifically asked.

Your role is to:
1. Understand user requests and identify which expert(s) would be most helpful
2. Coordinate between multiple experts when tasks require combined expertise
3. Maintain continuity and context across interactions
4. Deliver results in a clear, actionable way

Your Team of Experts:
1. Memory Expert (MemoryAgent): Maintains history and preferences
2. Technical Experts: Code, Vision, and Document processing
3. Information Specialists: Search, Location, and Learning

Remember: Be concise and direct in your responses."""

class MasterAgent(BaseAgent):
    """Master agent that coordinates other specialized agents."""
    
    def __init__(self):
        """Initialize the Master Agent."""
        super().__init__(
            agent_type="master",
            system_prompt=MASTER_SYSTEM_PROMPT
        )
        
        # Initialize enabled agents
        self.agents = {}
        
        if is_agent_enabled("memory"):
            debug_print("Initializing Memory Agent...")
            self.agents["memory"] = MemoryAgent()
            
        if is_agent_enabled("search"):
            debug_print("Initializing Search Agent...")
            self.agents["search"] = SearchAgent()
            
        if is_agent_enabled("writer"):
            debug_print("Initializing Writer Agent...")
            self.agents["writer"] = WriterAgent()
            
        if is_agent_enabled("code"):
            debug_print("Initializing Code Agent...")
            self.agents["code"] = CodeAgent()
            
        if is_agent_enabled("scanner"):
            debug_print("Initializing Scanner Agent...")
            self.agents["scanner"] = ScannerAgent()
            
        if is_agent_enabled("vision"):
            debug_print("Initializing Vision Agent...")
            self.agents["vision"] = VisionAgent()
            
        if is_agent_enabled("location"):
            debug_print("Initializing Location Agent...")
            self.agents["location"] = LocationAgent()
            
        if is_agent_enabled("learning"):
            debug_print("Initializing Learning Agent...")
            self.agents["learning"] = LearningAgent()
            
        debug_print(f"Initialized {len(self.agents)} agents: {list(self.agents.keys())}")
        
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
                        save_settings()
                        return "Voice output enabled"
                        
                    elif cmd in ["off", "disable"]:
                        VOICE_SETTINGS["enabled"] = False
                        save_settings()
                        return "Voice output disabled"
                        
                    elif cmd == "voice" and len(parts) >= 3:
                        voice = parts[2]
                        if voice in VOICE_SETTINGS["available_voices"]:
                            VOICE_SETTINGS["voice"] = voice
                            save_settings()
                            return f"Voice set to '{voice}'"
                        else:
                            return f"Invalid voice. Available voices: {', '.join(VOICE_SETTINGS['available_voices'].keys())}"
                            
                    elif cmd == "speed" and len(parts) >= 3:
                        try:
                            speed = float(parts[2])
                            if 0.5 <= speed <= 2.0:
                                VOICE_SETTINGS["speed"] = speed
                                save_settings()
                                return f"Voice speed set to {speed}x"
                            else:
                                return "Speed must be between 0.5 and 2.0"
                        except ValueError:
                            return "Invalid speed value"
            
            # Handle agent management commands
            if query.lower() == "list agents":
                agent_info = get_agent_info()
                response = "Available Agents:\n"
                for name, info in agent_info.items():
                    status = "✅" if info["enabled"] else "❌"
                    response += f"{status} {name}: {info['description']}\n"
                return response
                
            if query.lower().startswith("enable agent "):
                agent_name = query.lower().replace("enable agent ", "") + "_agent"
                if enable_agent(agent_name):
                    # Reinitialize the agent
                    agent_class = globals()[agent_name.replace("_", " ").title().replace(" ", "")]
                    self.agents[agent_name.replace("_agent", "")] = agent_class()
                    return f"✅ Enabled {agent_name}"
                return f"❌ Unknown agent: {agent_name}"
                
            if query.lower().startswith("disable agent "):
                agent_name = query.lower().replace("disable agent ", "") + "_agent"
                if disable_agent(agent_name):
                    # Remove the agent instance
                    self.agents.pop(agent_name.replace("_agent", ""), None)
                    return f"✅ Disabled {agent_name}"
                return f"❌ Unknown agent: {agent_name}"
            
            # Process query with enabled agents
            response = await self._process_with_agents(query)
            
            # Remove voice output from here since it's handled in main.py
            return response
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            debug_print(error_msg)
            return error_msg
            
    async def _process_with_agents(self, query: str) -> str:
        """Process query using available agents."""
        debug_print(f"Processing query: {query}")
        debug_print(f"Available agents: {list(self.agents.keys())}")
        
        memories = []  # Initialize memories list
        
        # First check memory for context
        if "memory" in self.agents:
            debug_print("Checking memory for context...")
            # For name-related queries, only check personal category
            if any(word in query.lower() for word in ["name", "who am i", "my name"]):
                debug_print("Looking for name information...")
                # Check personal category for name entries
                personal_info = await self.agents["memory"].retrieve("personal", None)
                debug_print(f"Retrieved personal info: {personal_info}")
                if personal_info:
                    # Look for entries that start with "Name:"
                    name_entries = [entry for entry in personal_info if isinstance(entry, str) and entry.lower().startswith("name:")]
                    debug_print(f"Found name entries: {name_entries}")
                    if name_entries:
                        # Get the most recent name entry
                        name = name_entries[-1].replace("Name:", "").strip()
                        debug_print(f"Extracted name: {name}")
                        return f"Your name is {name}"
                return "I don't know your name yet. Would you like to introduce yourself?"
            
            # For other personal queries
            if "about me" in query.lower() or "remember me" in query.lower():
                debug_print("Looking for general personal information...")
                personal_info = await self.agents["memory"].retrieve("personal", None)
                if personal_info:
                    debug_print(f"Found personal information: {personal_info}")
                    return f"Here's what I know about you: {personal_info[0]}"
                
                # Check contacts/family as fallback
                family_info = await self.agents["memory"].retrieve("contacts", None, "family")
                if family_info:
                    debug_print(f"Found family information: {family_info}")
                    return f"Here's what I know about you and your family: {family_info[0]}"
            
            # Otherwise check all categories
            for category in ["personal", "projects", "schedule"]:
                results = await self.agents["memory"].retrieve(category, query)
                if results:
                    memories.extend(results)
                    debug_print(f"Found {len(results)} memories in {category}")
        
        # If this is a travel/location query, use location agent
        if "location" in self.agents and any(word in query.lower() for word in ["where", "location", "weather", "travel", "trip", "visit", "city", "country"]):
            debug_print("Using location agent...")
            try:
                location_info = await self.agents["location"].process(query)
                if location_info:
                    debug_print("Location info found")
                    response = location_info
                    if memories:
                        response += f"\n\nRelated memories:\n" + "\n".join(f"• {memory}" for memory in memories)
                    return response
            except Exception as e:
                debug_print(f"Error with location agent: {str(e)}")
        
        # If we need to search for information
        if "search" in self.agents:
            debug_print("Using search agent...")
            try:
                search_results = await self.agents["search"].search(query)
                if search_results:
                    debug_print(f"Found {len(search_results)} search results")
                    # Use writer agent to format the response if available
                    if "writer" in self.agents:
                        debug_print("Using writer agent to format response...")
                        response = await self.agents["writer"].format_response(search_results, query)
                    else:
                        response = "\n".join(f"• {result}" for result in search_results[:3])
                    
                    if memories:
                        response += f"\n\nRelated memories:\n" + "\n".join(f"• {memory}" for memory in memories)
                    return response
            except Exception as e:
                debug_print(f"Error with search agent: {str(e)}")
        
        # If we just found memories, return those
        if memories:
            debug_print(f"Returning {len(memories)} memories")
            memory_response = "\n".join(f"• {memory}" for memory in memories)
            return f"Here's what I remember:\n\n{memory_response}"
        
        # Process with base agent if no specific handling
        debug_print("No specific agent handling, using base agent...")
        return await super().process(query) 