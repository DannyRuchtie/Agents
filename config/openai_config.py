"""OpenAI configuration module."""
import os
import base64
from typing import Dict, Any, List, Union

from openai import OpenAI

# OpenAI client singleton
_client = None

def get_client() -> OpenAI:
    """Get or create the OpenAI client singleton."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        _client = OpenAI()  # It will automatically use OPENAI_API_KEY from environment
    return _client

def encode_image(image_path: str) -> str:
    """Encode image to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def create_image_message(text: str, image_paths: Union[str, List[str]], detail: str = "auto") -> List[Dict]:
    """Create a message with text and images for vision model."""
    content = [{"type": "text", "text": text}]
    
    if isinstance(image_paths, str):
        image_paths = [image_paths]
    
    for path in image_paths:
        if path.startswith(("http://", "https://")):
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": path,
                    "detail": detail
                }
            })
        else:
            base64_image = encode_image(path)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}",
                    "detail": detail
                }
            })
    
    return content

# Default model settings
DEFAULT_MODEL = "gpt-4o-mini"  # Updated to use the mini vision model

DEFAULT_SETTINGS: Dict[str, Any] = {
    "seed": 42,  # For reproducibility
    "response_format": {"type": "text"},  # Ensure text responses
    "stream": False,  # Default to non-streaming
    "max_tokens": 4096,  # Standard context window
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
    },``
    "vision": {
        "model": DEFAULT_MODEL,
        "temperature": 0.2,  # Precise image analysis
        "max_tokens": 300,  # Shorter responses for image analysis
    }
}

def get_agent_config(agent_type: str) -> Dict[str, Any]:
    """Get the configuration for a specific agent type.
    
    Args:
        agent_type: The type of agent (master, memory, search, writer, code, vision)
        
    Returns:
        Configuration dictionary for the agent
    """
    config = AGENT_CONFIGS.get(agent_type, {}).copy()
    config.update(DEFAULT_SETTINGS)
    return config