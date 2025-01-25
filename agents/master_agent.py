"""Master agent that coordinates other specialized agents."""

from typing import Optional, Dict
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
        
        if is_agent_enabled("personality"):
            debug_print("Initializing Personality Agent...")
            from .personality_agent import PersonalityAgent
            self.agents["personality"] = PersonalityAgent()
            
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
        """Update system prompt with personal info from memory and personality insights."""
        try:
            # Get personal info from memory
            personal_info = await self.memory.retrieve("personal", None)
            family_info = await self.memory.retrieve("contacts", None, "family")
            
            # Extract name and family details from memory
            name_entries = [entry for entry in personal_info if isinstance(entry, str) and entry.lower().startswith("name:")]
            name = name_entries[-1].replace("Name:", "").strip() if name_entries else "Danny"
            
            # Get family details
            family_details = family_info[0] if family_info else ""
            
            # Get personality-aware prompt if available
            personality_prompt = ""
            if "personality" in self.agents:
                personality_prompt = await self.agents["personality"].get_personality_prompt()
            
            # Build dynamic system prompt
            self.system_prompt = f"""Hey! I'm {name}'s personal AI assistant and close friend. I know them really well - {family_details}

{personality_prompt}

I keep our chats natural and personal, drawing from everything I know about {name} and our past conversations. I focus on being genuinely helpful while keeping things friendly and fun."""

        except Exception as e:
            debug_print(f"Error updating system prompt: {str(e)}")
    
    async def process(self, query: str) -> str:
        """Process a user query and return a response."""
        # Update system prompt with latest memory and personality info
        await self.update_system_prompt()
        
        debug_print(f"\nProcessing query: {query}")
        try:
            # Check if this is a search query
            search_keywords = ["search", "look up", "find", "what is", "who is", "tell me about"]
            if any(keyword in query.lower() for keyword in search_keywords) and "search" in self.agents:
                debug_print("Using search agent to process query")
                return await self.agents["search"].process(query)
            
            # Process with other agents if not a search query
            response = await super().process(query)
            
            # Update personality insights if enabled
            if "personality" in self.agents:
                await self.agents["personality"].analyze_interaction(query, response)
            
            return response
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            debug_print(error_msg)
            return error_msg
            
    async def _process_with_agents(self, query: str) -> str:
        """Process query with appropriate agents."""
        try:
            # Get personality insights if available
            personality_insights = {}
            if self.personality_agent and self.personality_agent.is_enabled():
                personality_insights = await self.personality_agent.get_personality_insights()
            
            # Check for name-related queries
            if any(word in query.lower() for word in ["name", "who am i", "what's my name", "what is my name"]):
                name_entries = await self.memory_agent.get_memories("personal", "Name:")
                if name_entries:
                    name = name_entries[0]["content"].replace("Name: ", "")
                    timestamp = await self.memory_agent.get_timestamp("personal", name_entries[0]["content"])
                    
                    if "when" in query.lower() or "what time" in query.lower() or "how long" in query.lower():
                        if timestamp:
                            return f"I learned your name is {name} on {timestamp}!"
                        else:
                            return f"I know your name is {name}, but I'm not sure when I learned it."
                    else:
                        return f"Your name is {name}!"
                else:
                    return "I don't know your name yet. Would you like to introduce yourself?"
                
            # Check for family-related queries
            if any(word in query.lower() for word in ["family", "wife", "husband", "kids", "children"]):
                family_entries = await self.memory_agent.get_memories("family")
                if family_entries:
                    family_info = [entry["content"] for entry in family_entries]
                    return "Here's what I know about your family: " + " ".join(family_info)
                else:
                    return "I don't have any information about your family yet. Would you like to tell me about them?"
                
            # Check for search-specific queries
            search_keywords = ["what is", "who is", "tell me about", "search for", "look up", "find information"]
            if any(keyword in query.lower() for keyword in search_keywords):
                try:
                    search_results = await self.search_agent.search(query)
                    if search_results:
                        return search_results
                except Exception as e:
                    debug_print(f"Search failed: {str(e)}")
                    # Fall back to conversation mode
                    
            # Generate response using personality insights
            response = await self._generate_response(query, personality_insights)
            
            # Update personality traits based on interaction
            if self.personality_agent and self.personality_agent.is_enabled():
                await self.personality_agent.analyze_interaction(query, response)
            
            return response
            
        except Exception as e:
            debug_print(f"Error in _process_with_agents: {str(e)}")
            return "I encountered an error processing your request. Could you try rephrasing it?"
        
    async def _generate_response(self, query: str, personality_insights: Dict) -> str:
        """Generate a response considering personality insights."""
        try:
            # Customize response based on personality insights
            style = personality_insights.get("communication_style", {})
            interests = personality_insights.get("interests", {})
            traits = personality_insights.get("traits", {})
            
            # Adjust response style
            formality = style.get("formality_level", "informal")
            humor_level = style.get("humor_level", 5)
            emoji_usage = style.get("emoji_usage", 5)
            
            # Build system prompt with personality awareness
            system_prompt = f"""You are a friendly AI assistant who adapts to the user's style.
            Current communication preferences:
            - Formality: {formality}
            - Humor Level: {humor_level}/10
            - Emoji Usage: {emoji_usage}/10
            
            Top interests: {', '.join(sorted(interests.keys(), key=lambda k: interests[k], reverse=True)[:3])}
            
            Respond in a way that matches these preferences while maintaining a natural conversation flow.
            """
            
            # Generate response using the customized prompt
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
            
            response = await self.llm.chat_completion(messages)
            return response
            
        except Exception as e:
            debug_print(f"Error generating response: {str(e)}")
            return "I'm having trouble generating a response. Could you try again?" 