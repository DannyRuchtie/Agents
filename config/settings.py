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

# Voice settings
VOICE_SETTINGS = {
    "enabled": True,  # Voice output enabled by default
    "voice": "nova",  # Default voice
    "speed": 1.0,    # Default speed
    "available_voices": {
        "alloy": "Neutral and balanced",
        "echo": "Young and bright",
        "fable": "British and authoritative",
        "onyx": "Deep and powerful",
        "nova": "Energetic and friendly",
        "shimmer": "Clear and expressive"
    }
}

# Personality settings
PERSONALITY_SETTINGS = {
    "humor_level": 0.8,  # 0.0 to 1.0: serious to very humorous
    "formality_level": 0.2,  # 0.0 to 1.0: casual to very formal
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
    "debug_mode": False  # Debug mode off by default
}

def save_settings(settings_file: str = "config/settings.json") -> None:
    """Save current settings to a JSON file."""
    settings = {
        "agents": AGENT_SETTINGS,
        "voice": VOICE_SETTINGS,
        "personality": PERSONALITY_SETTINGS,
        "system": SYSTEM_SETTINGS
    }
    
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=4)
        
def load_settings(settings_file: str = "config/settings.json") -> None:
    """Load settings from a JSON file."""
    global AGENT_SETTINGS, VOICE_SETTINGS, PERSONALITY_SETTINGS, SYSTEM_SETTINGS
    
    if Path(settings_file).exists():
        with open(settings_file, 'r') as f:
            settings = json.load(f)
            AGENT_SETTINGS.update(settings.get('agents', {}))
            VOICE_SETTINGS.update(settings.get('voice', {}))
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

def is_voice_enabled() -> bool:
    """Check if voice output is enabled."""
    return VOICE_SETTINGS.get('enabled', False)

def enable_voice() -> None:
    """Enable voice output."""
    VOICE_SETTINGS['enabled'] = True
    save_settings()

def disable_voice() -> None:
    """Disable voice output."""
    VOICE_SETTINGS['enabled'] = False
    save_settings()

def set_voice(voice: str) -> bool:
    """Set the voice to use."""
    if voice in VOICE_SETTINGS['available_voices']:
        VOICE_SETTINGS['voice'] = voice
        save_settings()
        return True
    return False

def set_voice_speed(speed: float) -> bool:
    """Set the voice speed."""
    if 0.5 <= speed <= 2.0:
        VOICE_SETTINGS['speed'] = speed
        save_settings()
        return True
    return False

def get_voice_info() -> Dict[str, Any]:
    """Get voice settings information."""
    return {
        "enabled": VOICE_SETTINGS['enabled'],
        "current_voice": VOICE_SETTINGS['voice'],
        "current_speed": VOICE_SETTINGS['speed'],
        "available_voices": VOICE_SETTINGS['available_voices']
    }

def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return SYSTEM_SETTINGS.get('debug_mode', False)

def enable_debug() -> None:
    """Enable debug mode."""
    SYSTEM_SETTINGS['debug_mode'] = True
    save_settings()

def disable_debug() -> None:
    """Disable debug mode."""
    SYSTEM_SETTINGS['debug_mode'] = False
    save_settings()

def debug_print(*args, **kwargs) -> None:
    """Print only if debug mode is enabled."""
    if is_debug_mode():
        print(*args, **kwargs)

# Initialize settings
try:
    load_settings()
except Exception as e:
    print(f"Warning: Could not load settings file. Using defaults. Error: {e}")
    save_settings()  # Create default settings file 