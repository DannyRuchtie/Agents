"""OpenAI configuration module."""
import os
import base64
from typing import Dict, Any, List, Union

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# OpenAI client singleton
_client = None

def get_client() -> OpenAI:
    """Get or create the OpenAI client singleton."""
    global _client
    if _client is None:
        _client = OpenAI()  # Will use OPENAI_API_KEY from environment
    return _client

def encode_image(image_path: str) -> str:
    """Encode image to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def create_image_message(text: str, image_paths: Union[str, List[str]], detail: str = "auto") -> List[Dict]:
    """Create a message with text and images for vision model.
    
    Args:
        text: The text prompt for image analysis
        image_paths: Path(s) to image file(s) or URL(s)
        detail: Detail level for image analysis ("auto", "low", or "high")
        
    Returns:
        List of messages formatted for the vision model
    """
    if isinstance(image_paths, str):
        image_paths = [image_paths]
    
    # Create content array following the new format
    content = [
        {"type": "text", "text": text}
    ]
    
    # Add image content
    for path in image_paths:
        try:
            if path.startswith(("http://", "https://")):
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": path
                    }
                })
            else:
                print(f"Reading image file: {path}")
                base64_image = encode_image(path)
                print("Image encoded successfully")
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                })
        except Exception as e:
            print(f"Error processing image {path}: {str(e)}")
            raise
    
    print("Message content created successfully")
    return [{
        "role": "user",
        "content": content
    }]

# Default model settings
DEFAULT_MODEL = "gpt-4o-mini"  # Using GPT-4o mini model

DEFAULT_SETTINGS: Dict[str, Any] = {
    "model": DEFAULT_MODEL,
    "max_tokens": 300,
    "temperature": 0.7,
}

# Agent-specific configurations
AGENT_CONFIGS = {
    "master": {
        "temperature": 0.3,  # Balanced decision-making
        "seed": 123
    },
    "memory": {
        "temperature": 0.2,
        "seed": 456
    },
    "search": {
        "temperature": 0.2,
        "seed": 789
    },
    "writer": {
        "temperature": 0.4,
        "seed": 321
    },
    "code": {
        "temperature": 0.1,
        "seed": 654
    },
    "vision": {
        "model": "gpt-4o-mini",  # Using GPT-4o mini for vision tasks
        "temperature": 0.2,
        "max_tokens": 300,
        "seed": 987
    }
}

def get_agent_config(agent_type: str) -> Dict[str, Any]:
    """Get the configuration for a specific agent type.
    
    Args:
        agent_type: The type of agent (master, memory, search, writer, code, vision)
        
    Returns:
        Configuration dictionary for the agent
    """
    config = DEFAULT_SETTINGS.copy()
    config.update(AGENT_CONFIGS.get(agent_type, {}))
    return config