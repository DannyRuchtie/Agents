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
        "enabled": False,
        "description": "Provides location information and travel assistance"
    },
    "learning": {
        "enabled": True,
        "description": "Improves system through conversation monitoring"
    },
    "personality": {
        "enabled": True,
        "description": "Learns and adapts to user's personality and preferences"
    },
    "weather": {
        "enabled": True,
        "description": "Fetches weather forecasts from a local service"
    },
    "time": {
        "enabled": True,
        "description": "Provides the current date and time"
    },
    "screen": {
        "enabled": True,
        "description": "Captures the screen and uses VisionAgent to describe it"
    },
    "camera": {
        "enabled": True,
        "description": "Captures images from webcam and uses VisionAgent to describe them"
    }
}

# LLM Provider Settings
LLM_PROVIDER_SETTINGS = {
    "default_provider": "ollama",  # "openai" or "ollama"
    "ollama_base_url": "http://localhost:11434",
    "ollama_default_model": "gemma3:4b-it-q4_K_M", # User specified model
    "ollama_default_vision_model": "gemma3:4b-it-q4_K_M", # Updated: Use gemma3:4b for vision
    "openai_default_model": "gpt-4.1-nano-2025-04-14" # Updated OpenAI default model
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

# Personality Settings
PERSONALITY_TRAITS = {
    "communication_style": {
        "formality_level": 0.3,  # 0 = very casual, 1 = very formal
        "verbosity": 0.6,  # 0 = concise, 1 = detailed
        "humor_level": 0.7,  # 0 = serious, 1 = playful
        "emoji_usage": True,  # Whether to use emojis
    },
    "interests": [],  # List of user's interests
    "preferences": {
        "learning_style": "visual",  # visual, auditory, reading, kinesthetic
        "communication_medium": "text",  # text, voice, mixed
        "response_length": "medium",  # short, medium, long
        "technical_level": "medium",  # basic, medium, advanced
    },
    "traits": {
        "openness": 0.8,  # Openness to new experiences
        "conscientiousness": 0.7,  # Attention to detail
        "extraversion": 0.6,  # Social energy level
        "agreeableness": 0.8,  # Warmth in interactions
        "neuroticism": 0.3,  # Emotional sensitivity
    },
    "interaction_history": {
        "preferred_topics": [],  # Topics user frequently discusses
        "avoided_topics": [],  # Topics user tends to avoid
        "peak_activity_times": [],  # Times when user is most active
        "typical_session_length": "medium",  # short, medium, long
    }
}

# Voice settings
VOICE_SETTINGS = {
    "enabled": False,  # Voice output DISABLED by default
    "tts_provider": "openai", # 'openai' or 'system' (for previous Kokoro/macOS TTS)
    "openai_voice": "alloy",  # Default OpenAI voice model
    "openai_model": "tts-1", # Can be tts-1 or tts-1-hd
    "speed": 1.0,  # Default speed (OpenAI TTS takes 0.25 to 4.0)
    "available_openai_voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
    # Old system voice settings (can be kept for fallback or future use)
    "system_voice": "af_sarah", 
    "available_system_voices": {
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
    },
}

# System settings
SYSTEM_SETTINGS = {
    "os_type": "macos",  # Operating system
    "has_location_access": True,  # Whether location services are enabled
    "has_screen_access": True,  # Whether screen capture is enabled
    "debug_mode": True,  # Debug mode ON by default for now
    "app_path": str(Path(__file__).resolve().parent.parent) # Added app_path, resolves to project root
}

# Settings file path
SETTINGS_FILE = Path("config/settings.json")

def save_settings():
    """Save current settings to file."""
    settings = {
        "agent_settings": AGENT_SETTINGS,
        "llm_provider_settings": LLM_PROVIDER_SETTINGS,
        "personality_settings": PERSONALITY_SETTINGS,
        "personality_traits": PERSONALITY_TRAITS,
        "voice_settings": VOICE_SETTINGS,
        "system_settings": SYSTEM_SETTINGS
    }
    
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        debug_print("Settings saved successfully")
    except Exception as e:
        debug_print(f"Error saving settings: {str(e)}")

def load_settings():
    """Load settings from file."""
    global AGENT_SETTINGS, PERSONALITY_SETTINGS, PERSONALITY_TRAITS, VOICE_SETTINGS, SYSTEM_SETTINGS, LLM_PROVIDER_SETTINGS
    
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                
            AGENT_SETTINGS.update(settings.get("agent_settings", {}))
            LLM_PROVIDER_SETTINGS.update(settings.get("llm_provider_settings", {}))
            PERSONALITY_SETTINGS.update(settings.get("personality_settings", {}))
            PERSONALITY_TRAITS.update(settings.get("personality_traits", {}))
            VOICE_SETTINGS.update(settings.get("voice_settings", {}))
            SYSTEM_SETTINGS.update(settings.get("system_settings", {}))
            
            # Load sensitive keys from environment if not set directly in loaded JSON (for safety)
            # This allows .env to override or provide keys if they are missing from settings.json
            if VOICE_SETTINGS.get("picovoice_access_key") is None:
                VOICE_SETTINGS["picovoice_access_key"] = os.getenv("PICOVOICE_ACCESS_KEY")

            debug_print("Settings loaded successfully")
        except Exception as e:
            debug_print(f"Error loading settings: {str(e)}")

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

# Load settings on module import
load_settings() 