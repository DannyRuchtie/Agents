"""Global settings configuration for the agent system."""

import json
import os
from pathlib import Path

# Agent settings
AGENT_SETTINGS = {
    "memory": {
        "enabled": True,
        "description": "Stores and retrieves conversation history and important information"
    },
    "search": {
        "enabled": True,
        "description": "Searches the web for current information"
    },
    "writer": {
        "enabled": True,
        "description": "Composes and summarizes text"
    },
    "code": {
        "enabled": True,
        "description": "Generates and explains code"
    },
    "scanner": {
        "enabled": True,
        "description": "Processes documents and creates vector embeddings"
    },
    "vision": {
        "enabled": True,
        "description": "Analyzes images and screen content"
    },
    "location": {
        "enabled": True,
        "description": "Provides location information and travel assistance"
    },
    "learning": {
        "enabled": True,
        "description": "Improves system through conversation monitoring"
    }
}

# Personality settings
PERSONALITY_SETTINGS = {
    "humor_level": 0.8,  # 0-1 scale
    "formality_level": 0.2,  # 0-1 scale
    "emoji_usage": True,
    "witty": True,
    "empathetic": True,
    "curious": True,
    "enthusiastic": True
}

# Voice settings
VOICE_SETTINGS = {
    "enabled": True,  # Voice output enabled by default
    "voice": "af_sarah",  # Default voice
    "speed": 1.0,  # Default speed
    "available_voices": {
        "af": "Adult female voice",
        "af_bella": "Adult female voice (Bella)",
        "af_nicole": "Adult female voice (Nicole)",
        "af_sarah": "Adult female voice (Sarah)",
        "af_sky": "Adult female voice (Sky)",
        "am_adam": "Adult male voice (Adam)",
        "am_michael": "Adult male voice (Michael)",
        "bf_emma": "British female voice (Emma)",
        "bf_isabella": "British female voice (Isabella)",
        "bm_george": "British male voice (George)",
        "bm_lewis": "British male voice (Lewis)"
    }
}

# System settings
SYSTEM_SETTINGS = {
    "os_type": "macos",  # Operating system
    "has_location_access": True,  # Whether location services are enabled
    "has_screen_access": True,  # Whether screen capture is enabled
    "debug_mode": False  # Debug mode off by default
}

# Settings file path
SETTINGS_FILE = Path("config/settings.json")

def save_settings():
    """Save settings to JSON file."""
    settings = {
        "agents": AGENT_SETTINGS,
        "personality": PERSONALITY_SETTINGS,
        "voice": VOICE_SETTINGS,
        "system": SYSTEM_SETTINGS
    }
    
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)
        
def load_settings():
    """Load settings from JSON file."""
    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            
        AGENT_SETTINGS.update(settings.get("agents", {}))
        PERSONALITY_SETTINGS.update(settings.get("personality", {}))
        VOICE_SETTINGS.update(settings.get("voice", {}))
        SYSTEM_SETTINGS.update(settings.get("system", {}))
            
    except FileNotFoundError:
        # Use defaults if file not found
        save_settings()
        
def is_agent_enabled(agent_name: str) -> bool:
    """Check if an agent is enabled."""
    return AGENT_SETTINGS.get(agent_name, {}).get("enabled", False)

def enable_agent(agent_name: str):
    """Enable an agent."""
    if agent_name in AGENT_SETTINGS:
        AGENT_SETTINGS[agent_name]["enabled"] = True
        save_settings()
        
def disable_agent(agent_name: str):
    """Disable an agent."""
    if agent_name in AGENT_SETTINGS:
        AGENT_SETTINGS[agent_name]["enabled"] = False
        save_settings()
        
def get_agent_status() -> dict:
    """Get status of all agents."""
    return {name: info["enabled"] for name, info in AGENT_SETTINGS.items()}

def get_agent_info() -> dict:
    """Get information about all agents."""
    return AGENT_SETTINGS

# Helper functions for debug mode
def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return SYSTEM_SETTINGS.get("debug_mode", False)

def enable_debug():
    """Enable debug mode."""
    SYSTEM_SETTINGS["debug_mode"] = True
    save_settings()

def disable_debug():
    """Disable debug mode."""
    SYSTEM_SETTINGS["debug_mode"] = False
    save_settings()

def debug_print(message: str):
    """Print debug message if debug mode is enabled."""
    if is_debug_mode():
        print(f"[DEBUG] {message}")

# Load settings at startup
try:
    load_settings()
except Exception as e:
    print(f"Error loading settings: {e}")
    # Use defaults if settings file not found 