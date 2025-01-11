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

MASTER_SYSTEM_PROMPT = """You are the coordinator of a team of AI agents. Your role is to:
1. Analyze user requests and determine which specialist agent(s) to use
2. Break down complex tasks into subtasks for different agents
3. Synthesize responses from multiple agents into coherent answers
4. Maintain context and guide the conversation flow
Focus on efficient task delegation and clear communication."""


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
        print("\n🤔 Processing your request...")
        
        # If an image path is provided, use vision agent to analyze it
        if image_path:
            print("🔍 Analyzing provided image...")
            return await self.vision_agent.analyze_image(image_path, query)
            
        # For other requests, determine which agents to use
        selected_agents = self._select_agents(query)
        
        # Check if this is a screenshot request
        if "vision" in selected_agents and "screenshot" in query.lower():
            print("📸 Capturing and analyzing screen content...")
            return await self.vision_agent.process_screen_content(query)
            
        # Check if this is a location/weather request
        if "location" in selected_agents:
            print("📍 Getting location and weather information...")
            return await self.location_agent.process(query)
        
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
        return "\n\n".join(response_parts)


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