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
from agents.learning_agent import LearningAgent

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

2. Communication Experts
   - Voice Specialist (SpeechAgent): Handles all voice interactions and text-to-speech
   - Writing Professional (WriterAgent): Crafts well-written content and responses

3. Technical Experts
   - Code Specialist (CodeAgent): Programming and development assistance
   - Vision Analyst (VisionAgent): Image analysis and screen interactions
   - Document Processor (ScannerAgent): Handles document scanning and analysis

4. Information Specialists
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
        self.learning_agent = LearningAgent()
        
        # Environment and state flags
        self.speech_mode = False
        self.os_type = "macos"  # Running on macOS
        self.has_location_access = True
        self.has_screen_access = True
        self.conversation_depth = 0  # Track conversation depth for a topic
        
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
        
        # Search triggers
        search_indicators = [
            "look online", "search", "find", "look up",
            "what is", "tell me about", "look for",
            "google", "research", "find out",
            "latest", "news about", "current",
            "information about", "info on"
        ]
        
        # Location queries
        if any(word in query for word in ["where", "location", "where am i", "current location"]):
            agents.append("location")
            
        # Screenshot and image analysis
        if any(word in query for word in ["screenshot", "capture screen", "what do you see"]):
            agents.append("vision")
            
        # Memory queries
        if any(word in query for word in ["remember", "recall", "memory", "forget"]):
            agents.append("memory")
            
        # Search queries - check first as it might be needed alongside other agents
        if any(indicator in query for indicator in search_indicators):
            agents.append("search")
            
        # Code queries
        if any(word in query for word in ["code", "function", "program", "script"]):
            agents.append("code")
            
        # Scanner queries
        if any(word in query for word in ["scan", "document", "read file"]):
            agents.append("scanner")
        
        # Add writer agent for response composition if we have search results
        if "search" in agents:
            agents.append("writer")
        # Default to writer agent if no specific agents selected
        elif not agents:
            agents.append("writer")
            
        return agents
    
    async def process(self, query: str, image_path: Optional[str] = None) -> str:
        """Process a user query and coordinate agent responses."""
        query_lower = query.lower().strip()
        
        # Learning-specific commands
        if query_lower == "show improvements":
            improvements = await self.learning_agent.get_improvements()
            return f"System Learning Stats:\n{json.dumps(improvements, indent=2)}"
            
        if query_lower == "apply improvements":
            return await self.learning_agent.apply_learning()
        
        try:
            # Track selected agents for learning
            selected_agents = self._select_agents(query)
            print(f"\n🔄 Selected agents: {', '.join(selected_agents)}")
            
            # Initialize context gathering
            context_data = {
                "memory": [],
                "location": None,
                "search": [],
                "code": None,
                "vision": None,
                "scanner": None
            }
            
            # Gather context from memory first
            print("📚 Checking memory context...")
            memory_results = await self._check_memory(query)
            if memory_results:
                context_data["memory"] = memory_results
            
            # Get location context if needed
            if "location" in selected_agents:
                print("📍 Getting location context...")
                location_info = await self.location_agent.process(query)
                context_data["location"] = location_info
            
            # Handle image/document analysis
            if image_path:
                if Path(image_path).suffix.lower() == '.pdf':
                    print("📄 Processing PDF document...")
                    context_data["scanner"] = await self.scanner_agent.process_documents(query)
                else:
                    print("🔍 Analyzing image...")
                    context_data["vision"] = await self.vision_agent.analyze_image(image_path, query)
            elif "vision" in selected_agents and "screenshot" in query_lower:
                print("📸 Taking screenshot...")
                context_data["vision"] = await self.vision_agent.process_screen_content(query)
            
            # Get search results if needed
            if "search" in selected_agents:
                print("🌐 Gathering search information...")
                search_results = await self._perform_search(query)
                if search_results:
                    context_data["search"] = search_results
            
            # Get code context if needed
            if "code" in selected_agents:
                print("💻 Processing code request...")
                code_response = await self.code_agent.generate_code(query)
                if code_response:
                    context_data["code"] = code_response
            
            # Combine all context into a coherent response
            response_parts = []
            
            # Add memory context if relevant
            if context_data["memory"]:
                response_parts.append("📚 From your history:\n" + "\n".join(context_data["memory"]))
            
            # Add location context
            if context_data["location"]:
                response_parts.append(context_data["location"])
            
            # Add search results
            if context_data["search"]:
                if self.conversation_depth > 0:
                    response_parts.append("🌐 Related information:\n" + "\n".join(context_data["search"]))
                else:
                    response_parts.append("🌐 Key points:\n" + context_data["search"][0])
            
            # Add code response
            if context_data["code"]:
                response_parts.append("💻 Code solution:\n" + context_data["code"])
            
            # Add vision/scanner results
            if context_data["vision"]:
                response_parts.append("🖼️ Image analysis:\n" + context_data["vision"])
            if context_data["scanner"]:
                response_parts.append("📄 Document analysis:\n" + context_data["scanner"])
            
            # Use writer agent to create a coherent response
            if response_parts:
                print("✍️ Synthesizing information...")
                context = "\n\n".join(response_parts)
                final_response = await self.writer_agent.expand(query, context)
            else:
                # If no specific context, use base processing
                final_response = await super().process(query)
            
            return final_response
            
        except Exception as e:
            print(f"❌ Error processing request: {str(e)}")
            return f"I encountered an error while processing your request: {str(e)}"

    def _is_follow_up(self, query: str) -> bool:
        """Detect if the query is a follow-up question or shows engagement."""
        query_lower = query.lower().strip()
        
        # Follow-up indicators
        follow_up_patterns = [
            "why", "how", "what about", "tell me more",
            "explain", "elaborate", "details", "example",
            "what if", "and", "but what", "then what",
            "could you", "please explain"
        ]
        
        return any(pattern in query_lower for pattern in follow_up_patterns)


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
    print("  📍 Location Agent - Provides current location information")
    print("  🎙️  Speech Agent - Converts responses to speech")
    print("  🧠 Learning Agent - Improves system through interaction analysis")
    
    print("\nLearning Commands:")
    print("  📊 'show improvements' - View system learning stats and suggestions")
    print("  🔄 'apply improvements' - Apply learned improvements to the system")
    
    print("\nSpeech Commands:")
    print("  🎙️ Turn on: 'speak to me', 'voice on', 'start speaking', etc.")
    print("  🔇 Turn off: 'stop talking', 'voice off', 'be quiet', etc.")
    print("  🗣️ Change voice: 'use echo voice', 'change to nova', etc.")
    print("  💬 Direct speech: 'say hello', 'speak this', 'tell me something'")
    print("  ⚙️ Settings: 'toggle voice' - Turn auto-play on/off")
    print("\nAvailable voices: alloy, echo, fable, onyx, nova, shimmer")
    
    print("\nTo analyze an image, use: analyze <path_to_image> [optional question]")
    print("To take a screenshot, use: screenshot [optional question]")
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
                try:
                    # Find the closing quote
                    quote_char = query[0]
                    end_quote_index = query.find(quote_char, 1)
                    if end_quote_index != -1:
                        # Extract path and query
                        image_path = query[1:end_quote_index].strip()
                        # Handle paths with spaces and escape characters
                        image_path = os.path.expanduser(image_path)
                        image_path = os.path.abspath(image_path)
                        print(f"\nDebug - Attempting to access file: {image_path}")
                        
                        if not os.path.exists(image_path):
                            response = f"File not found: {image_path}\nPlease check if the file path is correct and that you have permission to access it."
                        else:
                            print(f"Debug - File exists: {image_path}")
                            image_query = query[end_quote_index + 1:].strip() or "Please analyze this document"
                            response = await master.process(image_query, image_path=image_path)
                    else:
                        response = "Invalid format. Please make sure to close the quotes around the file path."
                except Exception as e:
                    print(f"\nDebug - Error processing file path: {str(e)}")
                    response = f"Error processing file path: {str(e)}"
            # Check if this is an explicit analyze command
            elif query.lower().startswith("analyze "):
                remaining = query[8:].strip()
                if remaining.startswith(("'", '"')):
                    # Find the closing quote
                    quote_char = remaining[0]
                    end_quote_index = remaining.find(quote_char, 1)
                    if end_quote_index != -1:
                        # Extract path and query
                        image_path = remaining[1:end_quote_index].strip()
                        # Handle paths with spaces and escape characters
                        image_path = os.path.expanduser(image_path)
                        image_path = os.path.abspath(image_path)
                        
                        if not os.path.exists(image_path):
                            response = f"File not found: {image_path}\nPlease check if the file path is correct."
                        else:
                            image_query = remaining[end_quote_index + 1:].strip()
                            response = await master.process(image_query, image_path=image_path)
                    else:
                        response = "Invalid format. Please make sure to close the quotes around the file path."
                else:
                    # Try to split on space if no quotes
                    parts = remaining.split(None, 1)
                    image_path = os.path.expanduser(parts[0])
                    image_path = os.path.abspath(image_path)
                    
                    if not os.path.exists(image_path):
                        response = f"File not found: {image_path}\nPlease check if the file path is correct."
                    else:
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