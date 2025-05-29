"""Time agent for fetching and displaying the current date and time."""
import datetime
from .base_agent import BaseAgent
from config.settings import debug_print

TIME_SYSTEM_PROMPT = """You are a Time Agent. Your task is to provide the current date and time when asked."""

class TimeAgent(BaseAgent):
    """Agent for providing the current date and time."""

    def __init__(self):
        """Initialize the Time Agent."""
        super().__init__(
            agent_type="time",
            system_prompt=TIME_SYSTEM_PROMPT,
        )

    async def process(self, query: str = None) -> str:
        """Get the current date and time and return it as a formatted string."""
        debug_print(f"TimeAgent processing query: {query}")
        now = datetime.datetime.now()
        # Example: Tuesday, May 28, 2024 at 09:30 PM
        formatted_time = now.strftime("%A, %B %d, %Y at %I:%M %p") 
        
        response = f"The current date and time is {formatted_time}."
        debug_print(f"TimeAgent response: {response}")
        print(response) # Print the response for streaming-like behavior
        return response 