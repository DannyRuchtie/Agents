import asyncio
from dotenv import load_dotenv
from browser_use import Agent as BU_Agent # Renamed to avoid conflict if we name our class Agent
from langchain_openai import ChatOpenAI

from agents.base_agent import BaseAgent
from config.settings import debug_print

# Load environment variables (especially for API keys like OPENAI_API_KEY)
load_dotenv()

class BrowserAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_type="browser")
        # You might want to configure the LLM more globally or pass it via MasterAgent
        # For now, using the default recommended by browser-use
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0) # Ensure OPENAI_API_KEY is in .env
        debug_print("BrowserAgent initialized.")

    async def process(self, query: str) -> str:
        """
        Processes a query by using the browser-use agent to perform a web-based task.
        The query should be a natural language instruction for the browser task.
        Example: "Go to github.com and search for 'browser-use' and take a screenshot."
        """
        debug_print(f"BrowserAgent processing query: {query}")
        try:
            # Instantiate the browser-use Agent
            # The Agent from browser_use handles its own playwright setup internally.
            bu_agent_instance = BU_Agent(
                task=query,
                llm=self.llm,
                # You can add other browser-use Agent parameters here if needed:
                # e.g., viewport_size, playwright_kwargs, etc.
            )
            
            # Run the task
            # The browser-use agent typically logs its actions to the console.
            # The .run() method itself might not return a detailed string result for the master agent,
            # but rather performs the actions.
            await bu_agent_instance.run()
            
            # For now, return a confirmation. 
            # Future enhancements could involve capturing logs or specific outputs from browser-use.
            return f"Browser task '{query}' initiated and attempted by browser-use. Check console for detailed logs from browser-use."

        except ImportError as e:
            error_msg = f"BrowserAgent Error: A required library might be missing. {e}. Please ensure 'browser-use' and its dependencies are installed."
            debug_print(error_msg)
            return error_msg
        except Exception as e:
            # Catch other potential errors during browser-use execution
            error_msg = f"BrowserAgent encountered an error processing task '{query}': {e}"
            debug_print(error_msg)
            # Provide a more user-friendly message, details are in debug_print
            return f"Sorry, I couldn't complete the browser task due to an error: {type(e).__name__}."

# Example usage (for testing this agent directly)
async def main():
    # Ensure your OPENAI_API_KEY is set in your .env file or environment
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found. Please set it in your .env file.")
        return

    agent = BrowserAgent()
    # Test task 1: Simple navigation and screenshot
    # result1 = await agent.process("Go to example.com and take a screenshot, save it as example_com.png")
    # print(f"Test 1 Result: {result1}")

    # Test task 2: Search
    result2 = await agent.process("Go to duckduckgo.com and search for 'intelligent AI agents'")
    print(f"Test 2 Result: {result2}")
    
    # Test task 3: (More complex, ensure browser-use handles it)
    # result3 = await agent.process("Find the current price of Bitcoin on CoinMarketCap and tell me.")
    # print(f"Test 3 Result: {result3}")


if __name__ == "__main__":
    # This is for direct testing of BrowserAgent. 
    # You'll need to run this with Python: python -m agents.browser_agent
    # Make sure .env is in the root directory where you run this.
    import os
    # Add the project root to sys.path to allow relative imports if run directly
    if __package__ is None:
        import sys
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, os.path.dirname(SCRIPT_DIR)) # Add parent of 'agents' directory

    asyncio.run(main()) 