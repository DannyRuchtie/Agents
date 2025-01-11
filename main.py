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
from agents.screenshot_agent import ScreenshotAgent

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
        self.screenshot_agent = ScreenshotAgent()
    
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
    
    async def process(self, query: str) -> str:
        """Process a user query and coordinate agent responses."""
        print("\n🤔 Processing your request...")
        
        # First, determine which agents to use
        agent_selection = await self.process(
            f"Analyze this query and respond with ONLY the agent names needed (memory, search, writer, code, scanner, screenshot), "
            f"separated by commas. Choose only the essential agents for this task.\nQuery: {query}"
        )
        selected_agents = [a.strip().lower() for a in agent_selection.split(",")]
        
        tasks = []
        context = ""
        
        # Check if this is a screenshot request
        if "screenshot" in selected_agents:
            print("📸 Capturing and analyzing screen content...")
            screenshot_result = await self.screenshot_agent.process_screen_content(query)
            return screenshot_result
        
        # Memory check is always done first if memory agent is selected
        if "memory" in selected_agents:
            print("📚 Checking memory for relevant information...")
            memories = await self._check_memory(query)
            if memories:
                context += "Memory context:\n" + "\n".join(memories) + "\n\n"
        
        # Search is done next if selected
        if "search" in selected_agents:
            print("🌐 Searching the web for information...")
            search_results = await self._perform_search(query)
            if search_results:
                context += "Search results:\n" + "\n".join(search_results) + "\n\n"
        
        # Code generation if needed
        if "code" in selected_agents:
            print("💻 Preparing to generate code...")
            tasks.append(self.code_agent.generate_code(query))
        
        # Document scanning if needed
        if "scanner" in selected_agents:
            print("📄 Processing documents...")
            tasks.append(self.scanner_agent.process_documents(query))
        
        # Writer agent for composing the response if selected
        if "writer" in selected_agents:
            print("✍️ Composing response...")
            tasks.append(self.writer_agent.expand(query, context))
        elif context:  # If no writer but we have context, use base processing
            tasks.append(self.process(
                f"Based on this context and query, provide a clear and concise response:\n\n"
                f"Context:\n{context}\n\nQuery: {query}"
            ))
        
        # If no specific agents were selected, use base processing
        if not tasks:
            tasks.append(self.process(query))
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        # Combine results
        final_response = results[0]
        if len(results) > 1:
            final_response += f"\n\n💻 Here's some relevant code:\n{results[1]}"
        
        return final_response


async def chat_interface():
    """Interactive chat interface for the master agent."""
    # Initialize master agent
    print("\n🤖 Initializing AI Agents...")
    master = MasterAgent()
    
    print("\n🌟 Welcome to the Multi-Agent Chat Interface!")
    print("Available specialists:")
    print("  🔍 Search Agent - Searches the web for information")
    print("  ✍️  Writer Agent - Composes and summarizes text")
    print("  💻 Code Agent - Generates and explains code")
    print("  📚 Memory Agent - Stores and retrieves information")
    print("  📄 Scanner Agent - Manages document vectorization and search")
    print("  📸 Screenshot Agent - Capture and analyze screen content")
    print("\nType 'exit' to end the chat.")
    
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
            
            # Process the query
            response = await master.process_request(query)
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