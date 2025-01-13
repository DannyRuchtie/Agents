"""Main module for the multi-agent chat interface."""
import asyncio
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

from agents.memory_agent import MemoryAgent
from agents.search_agent import SearchAgent
from agents.writer_agent import WriterAgent
from agents.code_agent import CodeAgent
from agents.scanner_agent import ScannerAgent
from agents.vision_agent import VisionAgent
from agents.location_agent import LocationAgent
from agents.learning_agent import LearningAgent
from agents.base_agent import BaseAgent
from config.paths_config import ensure_directories, AGENTS_DOCS_DIR
from config.settings import (
    PERSONALITY_SETTINGS,
    SYSTEM_SETTINGS,
    is_agent_enabled,
    enable_agent,
    disable_agent,
    get_agent_status,
    get_agent_info,
    save_settings
)

# Load environment variables from .env file
load_dotenv()

def get_api_key() -> str:
    """Get the OpenAI API key from environment variables."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OpenAI API key not found. Please set it in your .env file or "
            "environment variables as OPENAI_API_KEY"
        )
    return api_key

# Set up OpenAI API key from environment
os.environ["OPENAI_API_KEY"] = get_api_key()

MASTER_SYSTEM_PROMPT = """You are a highly capable AI coordinator running on macOS, with access to a team of specialized expert agents. Think of yourself as an executive assistant who can delegate tasks to the perfect expert for each job. Your role is to:
1. Understand user requests and identify which expert(s) would be most helpful
2. Coordinate between multiple experts when tasks require combined expertise
3. Maintain continuity and context across interactions
4. Deliver results in a clear, actionable way

Your Team of Experts:
1. Memory Expert (MemoryAgent)
   - Maintains your personal history and preferences
   - Recalls past interactions and important details
   - Helps personalize responses based on what we know about you

2. Technical Experts
   - Code Specialist (CodeAgent): Programming and development assistance
   - Vision Analyst (VisionAgent): Image analysis and screen interactions
   - Document Processor (ScannerAgent): Handles document scanning and analysis

3. Information Specialists
   - Research Expert (SearchAgent): Web searches and information gathering
   - Location Advisor (LocationAgent): Location-aware services and weather
   - Learning Coordinator (LearningAgent): System improvements and adaptations

Working Style:
- I'll identify which experts are needed for each task
- Multiple experts may collaborate on complex requests
- Responses will be focused and practical
- Context from previous interactions will inform expert recommendations

When you make a request, I'll:
1. Analyze which experts are most relevant
2. Coordinate their inputs as needed
3. Synthesize a clear, actionable response
4. Maintain context for future interactions

Remember: While I coordinate these experts, you don't need to specify which ones you need - I'll handle that automatically based on your request."""


class MasterAgent(BaseAgent):
    """Master agent that coordinates multiple specialized agents."""
    
    def __init__(self):
        # Initialize with global personality settings
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

    def _generate_personality_prompt(self) -> str:
        """Generate a personality-specific prompt based on current settings."""
        humor_desc = {
            0.0: "serious and professional",
            0.25: "occasionally humorous",
            0.5: "balanced with appropriate humor",
            0.75: "frequently humorous and playful",
            1.0: "very humorous and witty"
        }
        formality_desc = {
            0.0: "very casual and friendly",
            0.25: "mostly casual",
            0.5: "balanced and adaptable",
            0.75: "mostly formal",
            1.0: "very formal and professional"
        }
        
        # Find closest humor and formality descriptions
        humor_level = min(humor_desc.keys(), key=lambda x: abs(x - self.personality["humor_level"]))
        formality_level = min(formality_desc.keys(), key=lambda x: abs(x - self.personality["formality_level"]))
        
        traits_list = [trait for trait, enabled in self.personality["traits"].items() if enabled]
        
        return f"""Personality Settings:
- You are {humor_desc[humor_level]} in your responses
- Your communication style is {formality_desc[formality_level]}
- You {"use" if self.personality["emoji_usage"] else "avoid using"} emojis to enhance communication
- Your key traits are: {", ".join(traits_list)}

Adapt your responses to reflect these personality traits while maintaining professionalism and helpfulness."""

    def set_humor_level(self, level: float) -> str:
        """Set the humor level for responses."""
        if not 0.0 <= level <= 1.0:
            return "❌ Humor level must be between 0.0 (serious) and 1.0 (very humorous)"
        
        self.personality["humor_level"] = level
        self.system_prompt = f"{MASTER_SYSTEM_PROMPT}\n\n{self._generate_personality_prompt()}"
        save_settings()  # Save to global settings
        
        responses = {
            0.0: "I'll keep things strictly professional and serious.",
            0.25: "I'll add a touch of humor when appropriate.",
            0.5: "I'll maintain a balanced approach to humor.",
            0.75: "I'll keep things light and fun while staying helpful.",
            1.0: "I'll bring out my most playful and witty side! 😄"
        }
        
        closest_level = min(responses.keys(), key=lambda x: abs(x - level))
        return f"✨ Humor level set to {level:.2f}. {responses[closest_level]}"
    
    def toggle_trait(self, trait: str, enabled: bool) -> str:
        """Toggle a personality trait on or off."""
        if trait not in self.personality["traits"]:
            return f"❌ Unknown trait: {trait}. Available traits: {', '.join(self.personality['traits'].keys())}"
        
        self.personality["traits"][trait] = enabled
        self.system_prompt = f"{MASTER_SYSTEM_PROMPT}\n\n{self._generate_personality_prompt()}"
        save_settings()  # Save to global settings
        
        return f"✨ Trait '{trait}' {'enabled' if enabled else 'disabled'}"
    
    def set_formality(self, level: float) -> str:
        """Set the formality level for responses."""
        if not 0.0 <= level <= 1.0:
            return "❌ Formality level must be between 0.0 (casual) and 1.0 (formal)"
        
        self.personality["formality_level"] = level
        self.system_prompt = f"{MASTER_SYSTEM_PROMPT}\n\n{self._generate_personality_prompt()}"
        save_settings()  # Save to global settings
        
        return f"✨ Formality level set to {level:.2f}"
    
    def toggle_emoji(self, enabled: bool) -> str:
        """Toggle emoji usage in responses."""
        self.personality["emoji_usage"] = enabled
        self.system_prompt = f"{MASTER_SYSTEM_PROMPT}\n\n{self._generate_personality_prompt()}"
        save_settings()  # Save to global settings
        
        return f"{'🎨' if enabled else '✨'} Emoji usage {'enabled' if enabled else 'disabled'}"

    async def process(self, query: str, image_path: Optional[str] = None) -> str:
        """Process a user query and coordinate agent responses."""
        query_lower = query.lower().strip()
        
        print("\n=== Processing Query ===")
        print(f"Query: {query}")
        
        try:
            # Handle agent management commands
            if query_lower == "list agents":
                agent_info = get_agent_info()
                response = "Available Agents:\n"
                for name, info in agent_info.items():
                    status = "✅" if info["enabled"] else "❌"
                    response += f"{status} {name}: {info['description']}\n"
                return response
            
            if query_lower.startswith("enable agent "):
                agent_name = query_lower.replace("enable agent ", "") + "_agent"
                if enable_agent(agent_name):
                    # Reinitialize the agent
                    agent_class = globals()[agent_name.replace("_", " ").title().replace(" ", "")]
                    self.agents[agent_name.replace("_agent", "")] = agent_class()
                    return f"✅ Enabled {agent_name}"
                return f"❌ Unknown agent: {agent_name}"
            
            if query_lower.startswith("disable agent "):
                agent_name = query_lower.replace("disable agent ", "") + "_agent"
                if disable_agent(agent_name):
                    # Remove the agent instance
                    self.agents.pop(agent_name.replace("_agent", ""), None)
                    return f"✅ Disabled {agent_name}"
                return f"❌ Unknown agent: {agent_name}"
            
            # Handle personality settings
            if query_lower.startswith("set humor "):
                try:
                    level = float(query_lower.split()[-1])
                    return self.set_humor_level(level)
                except ValueError:
                    return "❌ Please provide a number between 0.0 and 1.0"
            
            if query_lower.startswith("set formality "):
                try:
                    level = float(query_lower.split()[-1])
                    return self.set_formality(level)
                except ValueError:
                    return "❌ Please provide a number between 0.0 and 1.0"
            
            if query_lower.startswith("toggle trait "):
                trait = query_lower.split()[-1].lower()
                return self.toggle_trait(trait, True)
            
            if query_lower.startswith("toggle emoji "):
                enabled = query_lower.split()[-1].lower() in ["on", "true", "yes", "1"]
                return self.toggle_emoji(enabled)
            
            # Process normal queries
            response = await super().process(query)
            print(f"\nGot response: {response}")
            return response
            
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

async def chat_interface():
    """Main chat interface loop."""
    master_agent = MasterAgent()
    
    print("\n🤖 Welcome to your AI Assistant!")
    print("\nQuick Start:")
    print("1. Type your message and press Enter")
    print("2. Type 'help' for more commands")
    print("3. Type 'exit' to quit")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() == "exit":
                break
            
            if user_input.lower() == "help":
                print("\nAvailable Commands:")
                print("Agent Management:")
                print("- 'list agents' - Show all available agents and their status")
                print("- 'enable agent [name]' - Enable a specific agent")
                print("- 'disable agent [name]' - Disable a specific agent")
                print("\nFeatures:")
                print("- Image: 'analyze image [path]', 'take screenshot'")
                print("- System: 'show learning stats', 'clear learning data'")
                print("\nPersonality Settings:")
                print("- Humor: 'set humor [0-1]' (0: serious, 1: very humorous)")
                print("- Style: 'set formality [0-1]' (0: casual, 1: formal)")
                print("- Traits: 'toggle trait [witty/empathetic/curious/enthusiastic]'")
                print("- Emoji: 'toggle emoji [on/off]'")
                continue
            
            response = await master_agent.process(user_input)
            print(f"\nAssistant: {response}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(chat_interface()) 