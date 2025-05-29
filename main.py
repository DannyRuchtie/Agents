"""Main module for the multi-agent chat interface."""
import asyncio
import os
import sys
import select
import threading
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from agents.master_agent import MasterAgent
from agents.memory_agent import MemoryAgent
from agents.search_agent import SearchAgent
from agents.writer_agent import WriterAgent
from agents.code_agent import CodeAgent
from agents.scanner_agent import ScannerAgent
from agents.vision_agent import VisionAgent
from agents.location_agent import LocationAgent
from agents.learning_agent import LearningAgent
from utils.voice import voice_output

from config.paths_config import ensure_directories
from config.settings import (
    AGENT_SETTINGS,
    PERSONALITY_SETTINGS,
    VOICE_SETTINGS,
    SYSTEM_SETTINGS,
    is_agent_enabled,
    enable_agent,
    disable_agent,
    get_agent_status,
    get_agent_info,
    save_settings,
    is_debug_mode,
    debug_print
)

def check_input() -> Optional[str]:
    """Check for user input without blocking."""
    try:
        if select.select([sys.stdin], [], [], 0.0)[0]:
            return input().strip()
    except:
        pass
    return None

async def process_input(master_agent: MasterAgent, user_input: str):
    """Process user input and handle responses."""
    if not user_input:  # Skip empty input
        return
        
    # Stop any ongoing speech when new input is received
    voice_output.stop_speaking()
    
    # Handle simple stop command
    if user_input.lower() in ["stop", "voice stop"]:
        print("\nAssistant: Voice output stopped")
        return
    
    # Check for exit command
    if user_input.lower() == "exit":
        print("\nGoodbye! 👋")
        return "exit"
    
    # Voice control commands
    if user_input.lower() == "voice on" or user_input.lower() == "voice enable":
        if not VOICE_SETTINGS["enabled"]:
            VOICE_SETTINGS["enabled"] = True
            save_settings()
            print("\nAssistant: Voice output enabled. 🔊")
            voice_output.speak("Voice output enabled.") # Speak confirmation
        else:
            print("\nAssistant: Voice output is already enabled. 🔊")
        return # Command processed, no further MasterAgent processing needed

    if user_input.lower() == "voice off" or user_input.lower() == "voice disable":
        if VOICE_SETTINGS["enabled"]:
            voice_output.stop_speaking() # Stop any current speech first
            VOICE_SETTINGS["enabled"] = False
            save_settings()
            print("\nAssistant: Voice output disabled. 🔇")
            # Don't use voice_output.speak for this confirmation as it's being disabled
        else:
            print("\nAssistant: Voice output is already disabled. 🔇")
        return # Command processed

    if user_input.lower() == "voice status":
        status = "enabled" if VOICE_SETTINGS["enabled"] else "disabled"
        provider = VOICE_SETTINGS.get("tts_provider", "unknown")
        current_voice = VOICE_SETTINGS.get("openai_voice", "N/A") if provider == "openai" else VOICE_SETTINGS.get("system_voice", "N/A")
        status_msg = f"Voice output is currently {status}. Provider: {provider}, Voice: {current_voice}."
        print(f"\nAssistant: {status_msg}")
        if VOICE_SETTINGS["enabled"]:
             voice_output.speak(status_msg)
        return # Command processed

    # Check for help command
    if user_input.lower() == "help":
        help_text = "\nAvailable Commands:\nAgent Management:\n- list agents - Show all available agents and their status\n- enable agent [name] - Enable a specific agent\n- disable agent [name] - Disable a specific agent\n\nVoice Output:\n- voice status - Show voice output status\n- voice on/enable - Enable voice output\n- voice off/disable - Disable voice output\n- voice stop/stop - Stop current speech\n- voice voice [name] - Change voice\n- voice speed [value] - Change voice speed (0.5-2.0)"
        print(help_text)
        if VOICE_SETTINGS["enabled"]:
            voice_output.speak(help_text)
        return
    
    # Process query
    response = await master_agent.process(user_input)
    print(f"\nAssistant: {response}")
    
    # Speak response if voice is enabled - THIS IS NOW HANDLED BY MasterAgent
    # if VOICE_SETTINGS["enabled"] and not user_input.lower().startswith("voice"):
    #     debug_print("Speaking response with voice output")
    #     voice_output.speak(response)

def main():
    """Run the main chat interface."""
    # Load environment variables from .env file
    # Construct an absolute path to the .env file in the script's directory's parent (project root)
    script_dir = Path(__file__).resolve().parent
    env_path = script_dir / ".env" # Assumes .env is in the same directory as main.py
    # If main.py is in a subdirectory like 'src', and .env is in the project root, adjust accordingly:
    # env_path = script_dir.parent / ".env"
    
    print(f"[DEBUG] Attempting to load .env file from: {env_path}")
    # Load .env, override existing env vars if any, and be verbose if file not found
    loaded_successfully = load_dotenv(dotenv_path=env_path, override=True, verbose=True)
    print(f"[DEBUG] load_dotenv successful: {loaded_successfully}")

    # ---- TEMPORARY DEBUG ----
    # loaded_google_api_key = os.getenv("GOOGLE_API_KEY")
    # loaded_google_cse_id = os.getenv("GOOGLE_CSE_ID")
    # print(f"[DEBUG] Loaded GOOGLE_API_KEY: {loaded_google_api_key}")
    # print(f"[DEBUG] Loaded GOOGLE_CSE_ID: {loaded_google_cse_id}")
    # ---- END TEMPORARY DEBUG ----

    # Ensure directories exist
    ensure_directories()
    
    print("\nWelcome to the AI Assistant! Type 'help' for commands, 'exit' to quit.\n")
    
    async def chat_loop():
        master_agent = MasterAgent()
        prompt_shown = False
        
        while True:
            try:
                # Show input prompt only once if not shown
                if not prompt_shown:
                    print("\nYou: ", end="", flush=True)
                    prompt_shown = True
                
                # Check for input
                user_input = check_input()
                
                if user_input is not None:
                    # Process the input
                    result = await process_input(master_agent, user_input)
                    if result == "exit":
                        break
                    prompt_shown = False  # Reset prompt flag to show prompt again
                else:
                    await asyncio.sleep(0.1)  # Small delay to prevent CPU hogging
            
            except KeyboardInterrupt:
                print("\nGoodbye! 👋")
                break
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                debug_print(error_msg)
                print(f"\n{error_msg}")
                prompt_shown = False  # Reset prompt flag to show prompt again

    try:
        asyncio.run(chat_loop())
    finally:
        debug_print("Main loop ended. Shutting down voice output.")
        voice_output.shutdown() # Ensure voice output is shutdown cleanly

if __name__ == "__main__":
    main() 