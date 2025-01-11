"""OpenAI configuration module."""
import os
from typing import Dict, Any

from openai import OpenAI

# OpenAI client singleton
_client = None

def get_client() -> OpenAI:
    """Get or create the OpenAI client singleton."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

# Default model settings
DEFAULT_MODEL = "o1"  # O1 model for complex reasoning tasks
DEFAULT_SETTINGS: Dict[str, Any] = {
    "seed": 42,  # For reproducibility
    "response_format": {"type": "text"},  # Ensure text responses
    "stream": False,  # Default to non-streaming
}

# Agent-specific configurations
AGENT_CONFIGS = {
    "master": {
        "model": DEFAULT_MODEL,
        "temperature": 0.3,  # Balanced decision-making
    },
    "memory": {
        "model": DEFAULT_MODEL,
        "temperature": 0.2,  # Consistent memory retrieval
    },
    "search": {
        "model": DEFAULT_MODEL,
        "temperature": 0.2,  # Precise search terms
    },
    "writer": {
        "model": DEFAULT_MODEL,
        "temperature": 0.4,  # Balanced creativity and consistency
    },
    "code": {
        "model": DEFAULT_MODEL,
        "temperature": 0.1,  # Very precise code generation
    }
}

def get_agent_config(agent_type: str) -> Dict[str, Any]:
    """Get the configuration for a specific agent type.
    
    Args:
        agent_type: The type of agent (master, memory, search, writer, code)
        
    Returns:
        Configuration dictionary for the agent
    """
    config = AGENT_CONFIGS.get(agent_type, {}).copy()
    config.update(DEFAULT_SETTINGS)
    return config 