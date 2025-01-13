from typing import Optional
import re
import tempfile
import os
from config.settings import (
    PERSONALITY_SETTINGS,
    SYSTEM_SETTINGS,
    VOICE_SETTINGS,
    is_agent_enabled,
    enable_agent,
    disable_agent,
    get_agent_status,
    get_agent_info,
    save_settings,
    is_voice_enabled,
    enable_voice,
    disable_voice,
    set_voice,
    set_voice_speed,
    get_voice_info,
    is_debug_mode,
    enable_debug,
    disable_debug,
    debug_print
)

class MasterAgent(BaseAgent):
    """Master agent that coordinates all other agents."""
    
    def __init__(self):
        # Use global personality settings
        self.personality = PERSONALITY_SETTINGS.copy()
        
        # Update system prompt with personality
        personality_prompt = self._generate_personality_prompt()
        system_prompt = f"{MASTER_SYSTEM_PROMPT}\n\n{personality_prompt}"
        
        super().__init__(
            agent_type="master",
            system_prompt=system_prompt,
        )
        
        # Initialize enabled sub-agents
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
        
        # Environment and state flags from global settings
        self.os_type = SYSTEM_SETTINGS["os_type"]
        self.has_location_access = SYSTEM_SETTINGS["has_location_access"]
        self.has_screen_access = SYSTEM_SETTINGS["has_screen_access"]
        self.conversation_depth = 0  # Track conversation depth for a topic
        
        # Ensure required directories exist
        ensure_directories()
        
    async def process(self, query: str, image_path: Optional[str] = None) -> str:
        """Process a user query and coordinate agent responses."""
        query_lower = query.lower().strip()
        
        if is_debug_mode():
            debug_print("\n=== Processing Query ===")
            debug_print(f"Query: {query}")
        
        try:
            # Handle debug mode commands
            if query_lower in ["enable debug", "debug on"]:
                enable_debug()
                return "✅ Debug mode enabled"
                
            if query_lower in ["disable debug", "debug off"]:
                disable_debug()
                return "✅ Debug mode disabled"
                
            if query_lower == "debug status":
                return f"Debug mode is {'enabled' if is_debug_mode() else 'disabled'}"
            
            # First check memory for context
            memories = []
            if "memory" in self.agents:
                debug_print("\nSearching memory...")
                for category in ["personal", "projects", "schedule"]:
                    results = await self.agents["memory"].retrieve(category, query)
                    if results:
                        memories.extend(results)
                        debug_print(f"Found {len(results)} memories in {category}")
            
            # If this is a travel/location query, use location agent
            if any(word in query_lower for word in ["bali", "travel", "trip", "visit", "location", "weather"]):
                if "location" in self.agents:
                    debug_print("\nQuerying location agent...")
                    location_info = await self.agents["location"].get_location_info("Bali", query)
                    if location_info:
                        response = f"Here's what I found about Bali:\n{location_info}"
                        if memories:
                            response += f"\n\nFrom our previous discussions:\n" + "\n".join(f"• {memory}" for memory in memories)
                        
                        debug_print(f"\nGot response: {response}")
                        
                        # Store this interaction in memory
                        if "memory" in self.agents:
                            await self.agents["memory"].store("projects", f"Discussed Bali travel plans: {query}")
                        
                        # Speak the response if voice is enabled
                        if is_voice_enabled():
                            debug_print("\nStarting voice output...")
                            await voice_output.speak(response)
                            debug_print("Voice output complete")
                        
                        return response
            
            # If we need to search for information
            if "search" in self.agents and any(word in query_lower for word in ["find", "search", "look up", "what", "how", "when", "where"]):
                debug_print("\nPerforming web search...")
                search_results = await self.agents["search"].search(query)
                if search_results:
                    # Use writer agent to format the response if available
                    if "writer" in self.agents:
                        debug_print("\nFormatting search results...")
                        response = await self.agents["writer"].format_response(search_results, query)
                    else:
                        response = "\n".join(f"• {result}" for result in search_results[:3])
                    
                    if memories:
                        response += f"\n\nFrom our previous discussions:\n" + "\n".join(f"• {memory}" for memory in memories)
                    
                    debug_print(f"\nGot response: {response}")
                    
                    # Store this interaction in memory
                    if "memory" in self.agents:
                        await self.agents["memory"].store("projects", f"Searched for information: {query}")
                    
                    # Speak the response if voice is enabled
                    if is_voice_enabled():
                        debug_print("\nStarting voice output...")
                        await voice_output.speak(response)
                        debug_print("Voice output complete")
                    
                    return response
            
            # If we just found memories, return those
            if memories:
                debug_print(f"Found total of {len(memories)} memories")
                memory_response = "\n".join(f"• {memory}" for memory in memories)
                response = f"I found these relevant memories:\n\n{memory_response}"
                
                debug_print(f"\nGot response: {response}")
                
                # Speak the response if voice is enabled
                if is_voice_enabled():
                    debug_print("\nStarting voice output...")
                    await voice_output.speak(response)
                    debug_print("Voice output complete")
                
                return response
            
            # If no specific handling, use default processing
            response = await super().process(query)
            debug_print(f"\nGot response: {response}")
            
            # Speak the response if voice is enabled
            if is_voice_enabled():
                debug_print("\nStarting voice output...")
                await voice_output.speak(response)
                debug_print("Voice output complete")
            
            return response
            
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            debug_print(f"❌ {error_msg}")
            return error_msg 