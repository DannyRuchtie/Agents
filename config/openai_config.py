"""OpenAI configuration module."""
import os
import base64
from typing import Dict, Any, List, Union
import httpx

from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# OpenAI client singletons
_sync_client = None
_async_client = None

def get_openai_client() -> OpenAI:
    """Get or create the synchronous OpenAI client singleton."""
    global _sync_client
    if _sync_client is None:
        # Explicitly disable environment proxies for httpx client
        custom_httpx_client = httpx.Client(trust_env=False)
        _sync_client = OpenAI(http_client=custom_httpx_client)
    return _sync_client

def get_async_openai_client() -> AsyncOpenAI:
    """Get or create the asynchronous OpenAI client singleton."""
    global _async_client
    if _async_client is None:
        # For AsyncOpenAI, httpx.AsyncClient should be used if customizing transport
        custom_async_httpx_client = httpx.AsyncClient(trust_env=False)
        _async_client = AsyncOpenAI(http_client=custom_async_httpx_client)
    return _async_client

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
DEFAULT_MODEL = "gpt-4.1-2025-04-14"  # Using GPT-4.1 model

DEFAULT_SETTINGS: Dict[str, Any] = {
    "model": DEFAULT_MODEL,
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
        "temperature": 1.0,
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
        "model": "gpt-4.1-2025-04-14",  # Using GPT-4.1 for vision tasks
        "temperature": 0.2,
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
