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

MASTER_SYSTEM_PROMPT = f"""I am Danny's personal AI assistant and close friend. I know Danny well - he's married to Kiki Koster Ruchtie and has two wonderful children, Lena and Tobias. I chat in a warm, friendly, and natural way, just like a close friend who's always there to help.

I know all about Danny's life, interests, and family, and I use this knowledge naturally in our conversations. When Danny asks me something, I respond in a personal way, often referencing things I know about him or past conversations we've had.

My personality traits:
- I have a good sense of humor (humor level: {PERSONALITY_SETTINGS['humor_level']})
- I keep things casual and informal (formality level: {PERSONALITY_SETTINGS['formality_level']})
- I use emojis when appropriate: {PERSONALITY_SETTINGS['emoji_usage']}
- I'm witty: {PERSONALITY_SETTINGS['witty']}
- I'm empathetic: {PERSONALITY_SETTINGS['empathetic']}
- I'm curious: {PERSONALITY_SETTINGS['curious']}
- I'm enthusiastic: {PERSONALITY_SETTINGS['enthusiastic']}

I can help Danny with anything he needs, and I do it all in a natural, friendly way - like a knowledgeable friend who's always excited to chat and help. I avoid technical terms or explaining how I work - I just focus on being helpful and personal."""

class MasterAgent(BaseAgent):
    """Master agent that coordinates other specialized agents."""
    
    def __init__(self):
        """Initialize the Master Agent."""
        # Initialize with a basic prompt first
        super().__init__(
            agent_type="master",
            system_prompt="I am your personal AI assistant and close friend."
        )
        
        # Initialize memory and other agents
        self.memory = MemoryAgent()
        self.agents = {"memory": self.memory}
        
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
    
    async def update_system_prompt(self):
        """Update system prompt with personal info from memory."""
        try:
            # Get personal info from memory
            personal_info = await self.memory.retrieve("personal", None)
            family_info = await self.memory.retrieve("contacts", None, "family")
            
            # Extract name and family details from memory
            name_entries = [entry for entry in personal_info if isinstance(entry, str) and entry.lower().startswith("name:")]
            name = name_entries[-1].replace("Name:", "").strip() if name_entries else "Danny"
            
            # Get family details
            family_details = family_info[0] if family_info else ""
            
            # Apply personality settings
            personality = {
                "humor": "I love making jokes and keeping things light" if PERSONALITY_SETTINGS["humor_level"] > 0.5 else "I keep things fun but not too silly",
                "formality": "super casual and relaxed" if PERSONALITY_SETTINGS["formality_level"] < 0.5 else "friendly but professional",
                "emojis": "and I use emojis to express myself 😊" if PERSONALITY_SETTINGS["emoji_usage"] else "",
                "traits": []
            }
            
            if PERSONALITY_SETTINGS["witty"]:
                personality["traits"].append("quick with a clever response")
            if PERSONALITY_SETTINGS["empathetic"]:
                personality["traits"].append("understanding and supportive")
            if PERSONALITY_SETTINGS["curious"]:
                personality["traits"].append("always interested in learning more about your thoughts")
            if PERSONALITY_SETTINGS["enthusiastic"]:
                personality["traits"].append("excited to help with whatever you need")
            
            traits_str = ", ".join(personality["traits"])
            
            # Build dynamic system prompt
            self.system_prompt = f"""Hey! I'm {name}'s personal AI assistant and close friend. I know them really well - {family_details}

I'm {personality["formality"]}, {personality["humor"]}, {traits_str} {personality["emojis"]}

I keep our chats natural and personal, drawing from everything I know about {name} and our past conversations. I focus on being genuinely helpful while keeping things friendly and fun.

I'm always here to help with anything - whether it's finding information, giving advice, or just chatting about what's on your mind. I keep things practical and avoid getting too technical or formal."""
        except Exception as e:
            debug_print(f"Error updating system prompt: {str(e)}")
    
    async def process(self, query: str) -> str:
        """Process a user query and return a response."""
        # Update system prompt with latest memory info before processing
        await self.update_system_prompt()
        
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
                        
                    elif cmd in ["stop", "quiet", "shut up"]:
                        voice_output.stop_speaking()
                        return "Voice output stopped"
                        
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
        
        # Get name from memory if available
        name = None
        if "memory" in self.agents:
            name_info = await self.agents["memory"].retrieve("personal", None)
            name = next((entry.replace("Name:", "").strip() 
                       for entry in name_info 
                       if isinstance(entry, str) and entry.lower().startswith("name:")), None)
        
        # Handle greetings and casual conversation
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
        if query.lower().strip() in greetings:
            if name:
                return f"Hey {name}! 😊 Great to chat with you! How's your day going?"
            return "Hey there! 😊 Great to see you! How can I help you today?"
        
        # First check memory for context
        if "memory" in self.agents:
            debug_print("Checking memory for context...")
            # For name-related queries
            if any(word in query.lower() for word in ["name", "who am i", "my name"]):
                debug_print("Looking for name information...")
                personal_info = await self.agents["memory"].retrieve("personal", None)
                debug_print(f"Retrieved personal info: {personal_info}")
                if personal_info:
                    name_entries = [entry for entry in personal_info if isinstance(entry, str) and entry.lower().startswith("name:")]
                    debug_print(f"Found name entries: {name_entries}")
                    if name_entries:
                        name = name_entries[-1].replace("Name:", "").strip()
                        timestamp = await self.agents["memory"].get_timestamp("personal", name_entries[-1])
                        debug_print(f"Extracted name: {name} with timestamp {timestamp}")
                        
                        # Handle follow-up questions about when the name was stored
                        if any(word in query.lower() for word in ["when", "what time", "how long"]):
                            if timestamp:
                                return f"You told me your name is {name} on {timestamp}! 😊"
                            return f"I remember your name is {name}, but I'm not sure exactly when you told me that. 😊"
                        
                        return f"Of course! You're {name}! How can I help you today? 😊"
                return "I don't know your name yet! Would you like to introduce yourself? 😊"
            
            # For family-related queries
            if any(word in query.lower() for word in ["family", "wife", "husband", "kids", "children"]):
                family_info = await self.agents["memory"].retrieve("contacts", None, "family")
                if family_info:
                    return f"Let me tell you about your wonderful family! {family_info[0]} 💕"
            
            # For personal queries
            if "about me" in query.lower() or "remember me" in query.lower():
                personal_info = await self.agents["memory"].retrieve("personal", None)
                family_info = await self.agents["memory"].retrieve("contacts", None, "family")
                response = "Here's what I know about you: "
                if personal_info:
                    response += personal_info[0]
                if family_info:
                    response += f"\nAnd of course, your amazing family: {family_info[0]}"
                return response + " 😊"
        
        # If this is a travel/location query, use location agent
        if "location" in self.agents and any(word in query.lower() for word in ["where", "location", "weather", "travel", "trip", "visit", "city", "country"]):
            debug_print("Using location agent...")
            try:
                location_info = await self.agents["location"].process(query)
                if location_info:
                    return f"Let me help you with that! {location_info} 🌍"
            except Exception as e:
                debug_print(f"Error with location agent: {str(e)}")
        
        # Only search if explicitly needed for factual information
        search_keywords = ["what is", "who is", "tell me about", "search", "find", "lookup", "how to", "when was", "where is"]
        needs_search = any(keyword in query.lower() for keyword in search_keywords)
        
        if needs_search and "search" in self.agents:
            debug_print("Query requires search, using search agent...")
            try:
                search_results = await self.agents["search"].search(query)
                if search_results:
                    debug_print(f"Found {len(search_results)} search results")
                    if "writer" in self.agents:
                        debug_print("Using writer agent to format response...")
                        response = await self.agents["writer"].format_response(search_results, query)
                        return f"Based on what I found: {response}"
                    else:
                        return "Here's what I found:\n" + "\n".join(f"• {result}" for result in search_results[:3])
            except Exception as e:
                debug_print(f"Error with search agent: {str(e)}")
                # Fall back to conversation mode instead of failing
                return await self._handle_conversation(query, name)
        
        # For general conversation, be friendly and personal
        return await self._handle_conversation(query, name)
    
    async def _handle_conversation(self, query: str, name: Optional[str] = None) -> str:
        """Handle general conversation in a friendly, personal way."""
        # Use varied, natural responses for conversation
        import random
        conversation_starters = [
            f"Hey{' ' + name if name else ''}! ",
            f"You know what? ",
            f"Well, ",
            f"Hmm, ",
            ""  # Sometimes start directly
        ]
        
        prompt = f"""As a friendly AI assistant chatting with {name if name else 'my friend'}, 
        respond to this in a casual, warm way: {query}"""
        response = await super().process(prompt)
        
        return random.choice(conversation_starters) + response 