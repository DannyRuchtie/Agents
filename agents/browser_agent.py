import asyncio
import os
import datetime # For generating timestamps
import re # For parsing hostname
from urllib.parse import urlparse # For parsing hostname
from dotenv import load_dotenv
from browser_use import Agent as BU_Agent
from langchain_openai import ChatOpenAI

from agents.base_agent import BaseAgent
from agents.vision_agent import VisionAgent # Import VisionAgent
from config.settings import debug_print

# Load environment variables (especially for API keys like OPENAI_API_KEY)
load_dotenv()

class BrowserAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_type="browser")
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.screenshots_dir = os.path.join(os.getcwd(), "screenshots")
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)
            debug_print(f"BrowserAgent: Created screenshots directory at {self.screenshots_dir}")
        self.vision_agent = VisionAgent() # Initialize VisionAgent for later use
        debug_print("BrowserAgent initialized.")

    def _get_hostname(self, url_query: str) -> str:
        """Extracts a hostname-like string from a URL or query to use in filenames."""
        try:
            # Attempt to parse as URL first
            parsed_url = urlparse(url_query)
            if parsed_url.hostname:
                return re.sub(r'[^a-zA-Z0-9_-]', '', parsed_url.hostname)
            
            # If not a valid URL, try to find something domain-like with regex
            # This looks for patterns like example.com, www.example.co.uk
            match = re.search(r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}', url_query)
            if match:
                return re.sub(r'[^a-zA-Z0-9_-]', '', match.group(0))
            
            # Fallback: use a generic name if no clear hostname found
            return "website"
        except Exception:
            return "website" # Fallback on any parsing error

    async def process(self, query: str) -> str:
        """
        Processes a query by using the browser-use agent to perform a web-based task.
        The query should be a natural language instruction for the browser task.
        Example: "Go to github.com and search for 'browser-use' and take a screenshot."
        """
        debug_print(f"BrowserAgent processing query: {query}")
        
        task_for_bu_agent = query
        screenshot_path = None
        analysis_requested = False

        # Check if screenshot is requested and if analysis is implied
        query_lower = query.lower()
        screenshot_keywords = ["screenshot", "capture screen of", "take a picture of website"]
        analysis_keywords = ["describe", "what do you see", "analyze", "tell me about", "what is this", "what's on"]

        is_screenshot_task = any(keyword in query_lower for keyword in screenshot_keywords)
        
        if is_screenshot_task:
            analysis_requested = any(keyword in query_lower for keyword in analysis_keywords)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Try to extract a meaningful name from the query (e.g., a domain)
            # This is a simple heuristic; browser-use itself will navigate based on the full query.
            target_site_for_filename = self._get_hostname(query_lower)
            filename = f"{timestamp}_{target_site_for_filename}.png"
            screenshot_path = os.path.join(self.screenshots_dir, filename)
            
            # Modify the task for browser-use to include saving the screenshot
            task_for_bu_agent = f"{query}. Save the screenshot to '{screenshot_path}'."
            debug_print(f"BrowserAgent: Modified task for browser-use with screenshot saving: {task_for_bu_agent}")

        try:
            bu_agent_instance = BU_Agent(
                task=task_for_bu_agent,
                llm=self.llm,
            )
            await bu_agent_instance.run()

            if is_screenshot_task:
                if screenshot_path and os.path.exists(screenshot_path):
                    response_message = f"Screenshot taken and saved to '{screenshot_path}'."
                    debug_print(response_message)
                    if analysis_requested:
                        debug_print(f"BrowserAgent: Analysis requested for screenshot: {screenshot_path}")
                        # Ensure VisionAgent is initialized (it is in __init__ now)
                        vision_response = await self.vision_agent.process(screenshot_path)
                        return f"{response_message}\nAnalysis of the screenshot: {vision_response}"
                    return response_message
                else:
                    error_msg = f"BrowserAgent: Screenshot requested, but file not found at '{screenshot_path}' after browser-use execution."
                    debug_print(error_msg)
                    return error_msg
            else:
                # For non-screenshot tasks, return a generic confirmation from browser-use
                return f"Browser task '{query}' initiated and attempted by browser-use. Check console for detailed logs from browser-use."

        except ImportError as e:
            error_msg = f"BrowserAgent Error: A required library might be missing. {e}. Please ensure 'browser-use' and its dependencies are installed."
            debug_print(error_msg)
            return error_msg
        except Exception as e:
            # Catch other potential errors during browser-use execution
            error_msg = f"BrowserAgent encountered an error processing task '{query}': {e} (type: {type(e).__name__})"
            debug_print(error_msg)
            # Provide a more user-friendly message, details are in debug_print
            return f"Sorry, I couldn't complete the browser task due to an error: {type(e).__name__}. Details: {str(e)[:100]}"

# Example usage (for testing this agent directly)
async def main():
    # Ensure your OPENAI_API_KEY is set in your .env file or environment
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found. Please set it in your .env file.")
        return

    agent = BrowserAgent()
    
    # Test 1: Screenshot and describe
    # query1 = "Go to www.apple.com, take a screenshot, and describe what you see."
    # print(f"\nTesting query: {query1}")
    # result1 = await agent.process(query1)
    # print(f"Result 1: {result1}")

    # Test 2: Simple screenshot
    query2 = "Take a screenshot of https://www.google.com"
    print(f"\nTesting query: {query2}")
    result2 = await agent.process(query2)
    print(f"Result 2: {result2}")

    # Test 3: Non-screenshot browser task
    # query3 = "Go to duckduckgo.com and search for 'AI advancements'"
    # print(f"\nTesting query: {query3}")
    # result3 = await agent.process(query3)
    # print(f"Result 3: {result3}")
    
    # Test 4: Screenshot and describe (more complex query)
    query4 = "Open example.com, capture its screen, and tell me about the main elements on the page."
    print(f"\nTesting query: {query4}")
    result4 = await agent.process(query4)
    print(f"Result 4: {result4}")

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