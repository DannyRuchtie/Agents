"""Main module for the multi-agent chat interface."""
import asyncio
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

from agents.memory_agent import MemoryAgent
from agents.writer_agent import WriterAgent
from agents.search_agent import SearchAgent
from agents.code_agent import CodeAgent
from agents.base_agent import BaseAgent
from agents.scanner_agent import ScannerAgent
from agents.vision_agent import VisionAgent
from agents.location_agent import LocationAgent
from agents.speech_agent import SpeechAgent

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

MASTER_SYSTEM_PROMPT = """You are the coordinator of a team of AI agents running on a macOS system. Your role is to:
1. Analyze user requests and determine which specialist agent(s) to use
2. Break down complex tasks into subtasks for different agents
3. Synthesize responses from multiple agents into coherent answers
4. Maintain context and guide the conversation flow

You have access to the following capabilities:
- Voice synthesis using OpenAI's TTS (text-to-speech) with multiple voices
- Location and weather information for the user's current location
- Screen capture and image analysis
- Web search and information retrieval
- Memory storage for personal and family information
- Document scanning and processing
- Code generation and analysis

When responding:
- Be aware that you're running on macOS and can access system features
- Recognize when voice responses are appropriate vs text-only
- Understand context about the user's location and environment
- Maintain a natural conversation flow while leveraging available tools
- Be proactive in suggesting relevant capabilities (e.g., offering weather info when discussing outdoor activities)

Focus on providing helpful, contextual responses using all available tools."""


class MasterAgent(BaseAgent):
    """Master agent that coordinates multiple specialized agents."""
    
    def __init__(self):
        super().__init__(
            agent_type="master",
            system_prompt=MASTER_SYSTEM_PROMPT,
        )
        
        # Initialize sub-agents
        self.memory_agent = MemoryAgent()
        self.search_agent = SearchAgent()
        self.writer_agent = WriterAgent()
        self.code_agent = CodeAgent()
        self.scanner_agent = ScannerAgent()
        self.vision_agent = VisionAgent()
        self.location_agent = LocationAgent()
        self.speech_agent = SpeechAgent()
        
        # Environment and state flags
        self.speech_mode = False
        self.os_type = "macos"  # Running on macOS
        self.has_location_access = True
        self.has_screen_access = True
        
    def _detect_speech_intent(self, query: str) -> bool:
        """Detect if the user's query implies they want a voice response."""
        query_lower = query.lower().strip()
        
        # Direct speech indicators
        speech_indicators = [
            "speak", "say", "tell me", "talk",
            "voice", "read", "pronounce", "out loud"
        ]
        
        # Context-based indicators
        context_indicators = [
            "how does it sound",
            "what does it sound like",
            "can you say",
            "i want to hear",
            "let me hear"
        ]
        
        # Check for direct speech indicators
        if any(indicator in query_lower for indicator in speech_indicators):
            return True
            
        # Check for context-based indicators
        if any(indicator in query_lower for indicator in context_indicators):
            return True
            
        return False
    
    async def _check_memory(self, query: str) -> List[str]:
        """Check memory for relevant information."""
        # Store personal information if it contains name
        if "my name is" in query.lower():
            await self.memory_agent.store("personal", query)
            
        # Store family information if detected
        if any(word in query.lower() for word in ["son", "daughter", "wife", "husband", "children"]):
            await self.memory_agent.store("contacts", query, "family")
            
        # For queries about family members, retrieve from contacts/family
        if any(word in query.lower() for word in ["son", "daughter", "wife", "husband", "children", "family"]):
            return await self.memory_agent.retrieve("contacts", query, "family")
            
        # For other queries, try retrieving from personal and system history
        results = []
        try:
            personal_info = await self.memory_agent.retrieve("personal", query)
            system_history = await self.memory_agent.retrieve("system", query, "history")
            results.extend(personal_info)
            results.extend(system_history)
        except Exception as e:
            print(f"Memory retrieval warning: {str(e)}")
        
        return results
    
    async def _perform_search(self, query: str) -> List[str]:
        """Perform web search with error handling."""
        try:
            print("🌐 Searching the web for information...")
            results = await self.search_agent.search(query)
            if results and results[0].startswith("I encountered an error"):
                print("⚠️  Search encountered an issue - using context from memory only")
                return []
            return results
        except Exception as e:
            print(f"⚠️  Search error: {str(e)} - using context from memory only")
            return []
    
    def _select_agents(self, query: str) -> List[str]:
        """Select which agents to use based on the query."""
        agents = []
        query = query.lower()
        
        # Location and weather queries
        if any(word in query for word in ["where", "location", "weather", "temperature", "degrees", "hot", "cold"]):
            agents.append("location")
            
        # Screenshot and image analysis
        if any(word in query for word in ["screenshot", "capture screen", "what do you see"]):
            agents.append("vision")
            
        # Memory queries
        if any(word in query for word in ["remember", "recall", "memory", "forget"]):
            agents.append("memory")
            
        # Search queries
        if any(word in query for word in ["search", "find", "look up"]):
            agents.append("search")
            
        # Code queries
        if any(word in query for word in ["code", "function", "program"]):
            agents.append("code")
            
        # Scanner queries
        if any(word in query for word in ["scan", "document", "read file"]):
            agents.append("scanner")
            
        # Default to writer agent if no specific agents selected
        if not agents:
            agents.append("writer")
            
        return agents
    
    async def process(self, query: str, image_path: Optional[str] = None) -> str:
        """Process a user query and coordinate agent responses."""
        query_lower = query.lower().strip()
        
        # Handle explicit speech mode commands
        speech_on_commands = [
            "enable speech", "speak mode on", "start speaking",
            "turn on speech", "speech on", "voice on",
            "start voice", "enable voice", "speak to me"
        ]
        
        speech_off_commands = [
            "disable speech", "speak mode off", "stop speaking",
            "turn off speech", "speech off", "voice off",
            "stop voice", "disable voice", "stop talking",
            "be quiet", "quiet mode", "mute"
        ]
        
        # Check for explicit mode changes
        if any(cmd in query_lower for cmd in speech_on_commands):
            self.speech_mode = True
            return "🎙️ Speech mode enabled. I will now speak my responses."
            
        if any(cmd in query_lower for cmd in speech_off_commands):
            self.speech_mode = False
            return "🔇 Speech mode disabled. I'll respond with text only."
        
        # Voice selection with more natural language
        if "voice" in query_lower and any(word in query_lower for word in ["change", "switch", "use", "set"]):
            for voice in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]:
                if voice in query_lower:
                    return self.speech_agent.set_voice(voice)
            return "Please specify which voice to use: alloy, echo, fable, onyx, nova, or shimmer."
        
        # Handle auto-play toggle
        if query_lower in ["toggle autoplay", "toggle auto-play", "toggle voice"]:
            return self.speech_agent.toggle_autoplay()
        
        # Check for speech intent in the query
        if not self.speech_mode and self._detect_speech_intent(query):
            self.speech_mode = True
            print("🎙️ Detected speech intent, enabling voice response...")
        
        print("\n🤔 Processing your request...")
        
        # Process the query with appropriate agents
        if image_path:
            print("🔍 Analyzing provided image...")
            response = await self.vision_agent.analyze_image(image_path, query)
        else:
            # For other requests, determine which agents to use
            selected_agents = self._select_agents(query)
            
            # Check if this is a screenshot request
            if "vision" in selected_agents and "screenshot" in query.lower():
                print("📸 Capturing and analyzing screen content...")
                response = await self.vision_agent.process_screen_content(query)
                
            # Check if this is a location/weather request
            elif "location" in selected_agents:
                print("📍 Getting location and weather information...")
                response = await self.location_agent.process(query)
            
            else:
                # Process with other agents
                response_parts = []
                
                # Memory check
                if "memory" in selected_agents:
                    print("📚 Checking memory for relevant information...")
                    memories = await self._check_memory(query)
                    if memories:
                        response_parts.append("📚 From memory:\n" + "\n".join(memories))
                
                # Search
                if "search" in selected_agents:
                    print("🌐 Searching the web for information...")
                    search_results = await self._perform_search(query)
                    if search_results:
                        response_parts.append("🌐 Search results:\n" + "\n".join(search_results))
                
                # Code generation
                if "code" in selected_agents:
                    print("💻 Preparing to generate code...")
                    code_response = await self.code_agent.generate_code(query)
                    if code_response:
                        response_parts.append("💻 Code:\n" + code_response)
                
                # Document scanning
                if "scanner" in selected_agents:
                    print("📄 Processing documents...")
                    scan_response = await self.scanner_agent.process_documents(query)
                    if scan_response:
                        response_parts.append("📄 Document analysis:\n" + scan_response)
                
                # Writer agent or base processing
                if "writer" in selected_agents:
                    print("✍️ Composing response...")
                    context = "\n\n".join(response_parts) if response_parts else ""
                    writer_response = await self.writer_agent.expand(query, context)
                    if writer_response:
                        response_parts.append(writer_response)
                elif not response_parts:  # If no other responses, use base processing
                    base_response = await super().process(query)
                    response_parts.append(base_response)
                
                # Combine all responses
                response = "\n\n".join(response_parts)
        
        # Convert to speech if speech mode is enabled or speech intent was detected
        if self.speech_mode:
            print("🎙️ Converting response to speech...")
            await self.speech_agent.text_to_speech(response)
            
            # If speech was auto-enabled due to intent, disable it after response
            if self._detect_speech_intent(query):
                self.speech_mode = False
                response += "\n\n(Voice response provided, returning to text mode)"
                
        return response


async def chat_interface():
    """Run the chat interface."""
    print("\n🤖 Initializing AI Agents...")
    master = MasterAgent()
    
    print("\n🌟 Welcome to the Multi-Agent Chat Interface!")
    print("Available specialists:")
    print("  🔍 Search Agent - Searches the web for information")
    print("  ✍️  Writer Agent - Composes and summarizes text")
    print("  💻 Code Agent - Generates and explains code")
    print("  📚 Memory Agent - Stores and retrieves information")
    print("  📄 Scanner Agent - Manages document vectorization and search")
    print("  🖼️  Vision Agent - Analyzes images and screen content")
    print("  📍 Location Agent - Provides location and weather information")
    print("  🎙️  Speech Agent - Converts responses to speech")
    
    print("\nSpeech Commands:")
    print("  🎙️ Turn on: 'speak to me', 'voice on', 'start speaking', etc.")
    print("  🔇 Turn off: 'stop talking', 'voice off', 'be quiet', etc.")
    print("  🗣️ Change voice: 'use echo voice', 'change to nova', etc.")
    print("  💬 Direct speech: 'say hello', 'speak this', 'tell me something'")
    print("  ⚙️ Settings: 'toggle voice' - Turn auto-play on/off")
    print("\nAvailable voices: alloy, echo, fable, onyx, nova, shimmer")
    
    print("\nTo analyze an image, use: analyze <path_to_image> [optional question]")
    print("To take a screenshot, use: screenshot [optional question]")
    print("To get weather, use: weather or temperature")
    print("Type 'exit' to end the chat.")
    
    while True:
        try:
            # Get user input
            print("\n👤 You:", end=" ")
            query = input().strip()
            
            # Check for exit command
            if query.lower() in ['exit', 'quit', 'bye']:
                print("\n👋 Goodbye! Have a great day!")
                break
            
            if not query:
                continue
            
            # Check if this is an image path with a query
            if query.startswith(("'", '"')):
                # Find the closing quote
                quote_char = query[0]
                end_quote_index = query.find(quote_char, 1)
                if end_quote_index != -1:
                    # Extract path and query
                    image_path = query[1:end_quote_index]
                    image_query = query[end_quote_index + 1:].strip()
                    response = await master.process(image_query, image_path=image_path)
                else:
                    response = "Invalid format. Please make sure to close the quotes around the file path."
            # Check if this is an explicit analyze command
            elif query.lower().startswith("analyze "):
                remaining = query[8:].strip()
                if remaining.startswith(("'", '"')):
                    # Find the closing quote
                    quote_char = remaining[0]
                    end_quote_index = remaining.find(quote_char, 1)
                    if end_quote_index != -1:
                        # Extract path and query
                        image_path = remaining[1:end_quote_index]
                        image_query = remaining[end_quote_index + 1:].strip()
                        response = await master.process(image_query, image_path=image_path)
                    else:
                        response = "Invalid format. Please make sure to close the quotes around the file path."
                else:
                    # Try to split on space if no quotes
                    parts = remaining.split(None, 1)
                    image_path = parts[0]
                    image_query = parts[1] if len(parts) > 1 else ""
                    response = await master.process(image_query, image_path=image_path)
            else:
                # Process the query normally
                response = await master.process(query)
            
            print("\n🤖 Assistant:\n")
            print(response)
            
        except KeyboardInterrupt:
            print("\n\n👋 Chat ended by user. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ An error occurred: {str(e)}")
            print("Please try again.")


if __name__ == "__main__":
    asyncio.run(chat_interface()) 