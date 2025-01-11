"""Base agent module providing common functionality for all agents."""
from typing import Any, Dict, Optional

from config.openai_config import get_client, get_agent_config


class BaseAgent:
    """Base agent class with common functionality."""
    
    def __init__(
        self,
        agent_type: str,
        system_prompt: str = "You are a helpful AI assistant.",
    ):
        """Initialize the base agent.
        
        Args:
            agent_type: Type of agent (master, memory, search, writer, code)
            system_prompt: The system prompt for the agent
        """
        self.client = get_client()
        self.config = get_agent_config(agent_type)
        self.system_prompt = system_prompt
    
    async def process(self, input_text: str, **kwargs: Any) -> str:
        """Process the input text and return a response.
        
        Args:
            input_text: The input text to process
            **kwargs: Additional keyword arguments
            
        Returns:
            The processed response
        """
        # Merge kwargs with default config
        config = self.config.copy()
        config.update(kwargs)
        
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": input_text}
            ],
            **config
        )
        return response.choices[0].message.content 