"""Global settings configuration for the agent system."""

import json
import os
from pathlib import Path

# Agent settings - Streamlined architecture with core agents only
AGENT_SETTINGS = {
    "memory": {
        "enabled": True,
        "use_mem0": False,
        "description": "Stores and retrieves conversation history, personal information, and personality insights with intelligent semantic search"
    },
    "search": {
        "enabled": True,
        "description": "Searches the web for current information"
    }
}

# LLM Provider Settings
LLM_PROVIDER_SETTINGS = {
    "default_provider": "ollama",  # "openai" or "ollama" - Defaulting to Ollama for local-first workflows
    "ollama_base_url": "http://localhost:11434",
    "ollama_default_model": "gemma3:4b-it-q4_K_M",  # User specified model
    "ollama_default_vision_model": "gemma3:4b-it-q4_K_M",  # Use gemma3:4b for vision
    "openai_default_model": "gpt-4o-mini"  # Latest cost-effective model
}

# Auto Model Selector Settings - Intelligently routes to appropriate model based on complexity
MODEL_SELECTOR_SETTINGS = {
    "enabled": True,
    "simple_model": "gpt-4o-mini",  # For definitions, basic queries
    "moderate_model": "gpt-5-mini",  # For summaries, search synthesis
    "complex_model": "gpt-5",  # For deep analysis, multi-step reasoning
    "reasoning_model": "o1",  # For complex logical reasoning and problem-solving
    "vision_model": "gpt-5",  # For image analysis and vision tasks
    "realtime_model": "gpt-realtime-mini-2025-10-06",  # For real-time audio conversations
    "use_ollama_for_simple": True,  # Cost optimization - use local Ollama for simple tasks
    "complexity_threshold_tokens": {
        "simple": 50,  # Queries under 50 tokens are considered simple
        "complex": 100  # Queries over 100 tokens are considered complex
    },
    "complexity_keywords": {
        "simple": ["what is", "define", "who is", "summary", "summarize", "example of", "why is"],
        "complex": ["explain in detail", "analyze", "step by step", "provide a detailed", "calculate", 
                   "prove", "derive", "compare", "contrast", "advantages", "disadvantages"]
    }
}

# Mem0 Settings - Enhanced memory system with semantic search
# NOTE: Requires Python 3.11+ - Currently disabled on Python 3.9
MEM0_SETTINGS = {
    "enabled": False,
    "user_id": "danny",  # Primary user identifier
    "embedding_model": "text-embedding-3-small",  # OpenAI embedding model for semantic search
    "vector_store": "chroma",  # Vector database: "chroma", "qdrant", or "pinecone"
    "memory_decay_days": 90,  # Days after which memories start to decay in relevance
    "max_memories_per_query": 10,  # Maximum number of relevant memories to retrieve per query
    "similarity_threshold": 0.7  # Minimum similarity score for memory retrieval (0-1)
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
    "tts_provider": "openai",  # 'openai', 'system', or 'realtime'
    "openai_voice": "alloy",  # Default OpenAI voice model for TTS
    "openai_model": "tts-1",  # Can be tts-1 or tts-1-hd
    "speed": 1.0,  # Default speed (OpenAI TTS takes 0.25 to 4.0)
    "available_openai_voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
    # Realtime API settings for real-time voice conversations
    "realtime_enabled": False,  # Enable for real-time voice conversations
    "realtime_model": "gpt-realtime-mini-2025-10-06",  # Latest realtime model
    "realtime_voice": "alloy",  # Voice for realtime conversations
    "audio_format": "pcm16",  # Audio format: "pcm16", "g711_ulaw", or "g711_alaw"
    "realtime_temperature": 0.8,  # Temperature for realtime model
    "realtime_max_tokens": 4096,  # Max output tokens for realtime
    # Old system voice settings (kept for fallback)
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
    "debug_mode": False,  # Debug mode OFF by default; enable via settings if needed
    "app_path": str(Path(__file__).resolve().parent.parent) # Added app_path, resolves to project root
}

# Settings file path
SETTINGS_FILE = Path("config/settings.json")

def save_settings():
    """Save current settings to file."""
    settings = {
        "agent_settings": AGENT_SETTINGS,
        "llm_provider_settings": LLM_PROVIDER_SETTINGS,
        "model_selector_settings": MODEL_SELECTOR_SETTINGS,
        "mem0_settings": MEM0_SETTINGS,
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
    global AGENT_SETTINGS, PERSONALITY_SETTINGS, PERSONALITY_TRAITS, VOICE_SETTINGS, SYSTEM_SETTINGS, LLM_PROVIDER_SETTINGS, MODEL_SELECTOR_SETTINGS, MEM0_SETTINGS
    
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                
            loaded_agent_settings = settings.get("agent_settings", {})
            for key, value in loaded_agent_settings.items():
                if key in AGENT_SETTINGS and isinstance(value, dict):
                    AGENT_SETTINGS[key].update(value)
            LLM_PROVIDER_SETTINGS.update(settings.get("llm_provider_settings", {}))
            MODEL_SELECTOR_SETTINGS.update(settings.get("model_selector_settings", {}))
            MEM0_SETTINGS.update(settings.get("mem0_settings", {}))
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
