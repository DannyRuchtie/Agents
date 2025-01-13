"""Global settings configuration for the agent system."""
from typing import Dict, Any
import json
from pathlib import Path

# Default agent settings
AGENT_SETTINGS = {
    "memory_agent": {
        "enabled": True,
        "description": "Maintains personal history and preferences"
    },
    "search_agent": {
        "enabled": True,
        "description": "Web searches and information gathering"
    },
    "writer_agent": {
        "enabled": True,
        "description": "Content writing and response formatting"
    },
    "code_agent": {
        "enabled": True,
        "description": "Programming and development assistance"
    },
    "scanner_agent": {
        "enabled": True,
        "description": "Document scanning and analysis"
    },
    "vision_agent": {
        "enabled": True,
        "description": "Image analysis and screen interactions"
    },
    "location_agent": {
        "enabled": True,
        "description": "Location-aware services and weather"
    },
    "learning_agent": {
        "enabled": True,
        "description": "System improvements and adaptations"
    }
}

# Personality settings
PERSONALITY_SETTINGS = {
    "humor_level": 0.5,  # 0.0 to 1.0: serious to very humorous
    "formality_level": 0.5,  # 0.0 to 1.0: casual to very formal
    "emoji_usage": True,  # Whether to use emojis in responses
    "traits": {
        "witty": True,
        "empathetic": True,
        "curious": True,
        "enthusiastic": True
    }
}

# System settings
SYSTEM_SETTINGS = {
    "os_type": "macos",
    "has_location_access": True,
    "has_screen_access": True,
    "debug_mode": False
}

def save_settings(settings_file: str = "config/settings.json") -> None:
    """Save current settings to a JSON file."""
    settings = {
        "agents": AGENT_SETTINGS,
        "personality": PERSONALITY_SETTINGS,
        "system": SYSTEM_SETTINGS
    }
    
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=4)
        
def load_settings(settings_file: str = "config/settings.json") -> None:
    """Load settings from a JSON file."""
    global AGENT_SETTINGS, PERSONALITY_SETTINGS, SYSTEM_SETTINGS
    
    if Path(settings_file).exists():
        with open(settings_file, 'r') as f:
            settings = json.load(f)
            AGENT_SETTINGS.update(settings.get('agents', {}))
            PERSONALITY_SETTINGS.update(settings.get('personality', {}))
            SYSTEM_SETTINGS.update(settings.get('system', {}))

def is_agent_enabled(agent_name: str) -> bool:
    """Check if an agent is enabled."""
    return AGENT_SETTINGS.get(agent_name, {}).get('enabled', False)

def enable_agent(agent_name: str) -> bool:
    """Enable an agent."""
    if agent_name in AGENT_SETTINGS:
        AGENT_SETTINGS[agent_name]['enabled'] = True
        save_settings()
        return True
    return False

def disable_agent(agent_name: str) -> bool:
    """Disable an agent."""
    if agent_name in AGENT_SETTINGS:
        AGENT_SETTINGS[agent_name]['enabled'] = False
        save_settings()
        return True
    return False

def get_agent_status() -> Dict[str, Any]:
    """Get the status of all agents."""
    return {name: config['enabled'] for name, config in AGENT_SETTINGS.items()}

def get_agent_info() -> Dict[str, Any]:
    """Get detailed information about all agents."""
    return AGENT_SETTINGS

# Initialize settings
try:
    load_settings()
except Exception as e:
    print(f"Warning: Could not load settings file. Using defaults. Error: {e}")
    save_settings()  # Create default settings file 