"""Main module for the multi-agent chat interface."""
import asyncio
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv

from agents.memory_agent import MemoryAgent
from agents.writer_agent import WriterAgent
from agents.search_agent import SearchAgent
from agents.code_agent import CodeAgent
from agents.base_agent import BaseAgent

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
    
    async def _check_memory(self, query: str) -> List[str]:
        """Check if we have relevant information in memory."""
        return await self.memory_agent.retrieve(query)
    
    async def _needs_code(self, query: str) -> bool:
        """Determine if the query requires code generation."""
        response = await self.process(
            f"Does this query require code generation or programming examples? "
            f"Query: {query}\nRespond with just 'yes' or 'no'."
        )
        return response.lower().strip() == "yes"
    
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
    
    async def process_request(self, query: str) -> str:
        """Process a user request using the appropriate agents."""
        print("\n🤔 Processing your request...")
        
        # First, determine which agents to use
        agent_selection = await self.process(
            f"Analyze this query and respond with ONLY the agent names needed (memory, search, writer, code), "
            f"separated by commas. Choose only the essential agents for this task.\nQuery: {query}"
        )
        selected_agents = [a.strip().lower() for a in agent_selection.split(",")]
        
        tasks = []
        context = ""
        
        # Memory check is always done first if memory agent is selected
        if "memory" in selected_agents:
            print("📚 Checking memory for relevant information...")
            memories = await self._check_memory(query)
            if memories:
                print("🔍 Found relevant memories!")
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
        
        # Store the interaction in memory
        print("💾 Storing interaction in memory...")
        await self.memory_agent.store(
            "interactions",
            f"Query: {query}\nResponse: {final_response[:200]}..."  # Store truncated version
        )
        
        return final_response


async def chat_interface():
    """Interactive chat interface for the master agent."""
    # Set up OpenAI API key
    os.environ["OPENAI_API_KEY"] = "OPENAI_API_KEY_PLACEHOLDER"
    
    # Initialize master agent
    print("\n🤖 Initializing AI Agents...")
    master = MasterAgent()
    
    print("\n🌟 Welcome to the Multi-Agent Chat Interface!")
    print("Available specialists:")
    print("  🔍 Search Agent - Searches the web for information")
    print("  ✍️  Writer Agent - Composes and summarizes text")
    print("  💻 Code Agent - Generates and explains code")
    print("  📚 Memory Agent - Stores and retrieves information")
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