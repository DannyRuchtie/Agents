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
        # Create messages list
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": input_text}
        ]
        
        # Extract model and temperature from config
        config = {
            "model": self.config["model"],
            "temperature": self.config.get("temperature", 0.7),
            "max_tokens": self.config.get("max_tokens", 4096)
        }
        config.update(kwargs)  # Allow overriding with kwargs
        
        response = self.client.chat.completions.create(
            messages=messages,
            **config
        )
        return response.choices[0].message.content 