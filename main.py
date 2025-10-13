"""Main module for the multi-agent chat interface."""
import argparse
import asyncio
import os
import select
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from agents.master_agent import MasterAgent
from utils.voice import voice_output

from config.paths_config import ensure_directories
from config.help_text import HELP_TEXT
from config.settings import (
    VOICE_SETTINGS,
    SYSTEM_SETTINGS,
    save_settings,
    debug_print,
    LLM_PROVIDER_SETTINGS
)

# --- STT Instance and Command Queue ---
# Removed all STT and wake word logic

def check_input() -> Optional[str]:
    """Check for user input from stdin without blocking."""
    try:
        if sys.stdin in select.select([sys.stdin], [], [], 0.0)[0]:
            line = sys.stdin.readline().strip()
            if line:
                return line
    except Exception as e:
        debug_print(f"Error reading from stdin: {e}")
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
    
    # Voice control commands - TTS
    if user_input.lower() == "voice on" or user_input.lower() == "voice enable":
        if not VOICE_SETTINGS["enabled"]:
            VOICE_SETTINGS["enabled"] = True
            save_settings()
            print("\nAssistant: Voice output enabled. 🔊")
            voice_output.speak("Voice output enabled.") # Speak confirmation
        else:
            print("\nAssistant: Voice output is already enabled. 🔊")
        return

    if user_input.lower() == "voice off" or user_input.lower() == "voice disable":
        if VOICE_SETTINGS["enabled"]:
            voice_output.stop_speaking() # Stop any current speech first
            VOICE_SETTINGS["enabled"] = False
            save_settings()
            print("\nAssistant: Voice output disabled. 🔇")
        else:
            print("\nAssistant: Voice output is already disabled. 🔇")
        return

    if user_input.lower() == "voice status":
        status = "enabled" if VOICE_SETTINGS["enabled"] else "disabled"
        provider = VOICE_SETTINGS.get("tts_provider", "unknown")
        current_voice = VOICE_SETTINGS.get("openai_voice", "N/A") if provider == "openai" else VOICE_SETTINGS.get("system_voice", "N/A")
        status_msg = f"Voice output (TTS) is currently {status}. Provider: {provider}, Voice: {current_voice}."
        print(f"\nAssistant: {status_msg}")
        if VOICE_SETTINGS["enabled"]:
             voice_output.speak(status_msg)
        return

    if user_input.lower().startswith("voice voice "):
        parts = user_input.split(" ", 2)
        if len(parts) == 3:
            new_voice_name = parts[2].strip().lower()
            if VOICE_SETTINGS.get("tts_provider") == "openai":
                if new_voice_name in VOICE_SETTINGS.get("available_openai_voices", []):
                    VOICE_SETTINGS["openai_voice"] = new_voice_name
                    save_settings()
                    feedback_msg = f"OpenAI TTS voice changed to {new_voice_name}."
                    print(f"\nAssistant: {feedback_msg}")
                    if VOICE_SETTINGS["enabled"]: voice_output.speak(feedback_msg)
                else:
                    available_voices_str = ", ".join(VOICE_SETTINGS.get("available_openai_voices", []))
                    error_msg = f"Invalid OpenAI voice '{new_voice_name}'. Available: {available_voices_str}."
                    print(f"\nAssistant: {error_msg}")
                    if VOICE_SETTINGS["enabled"]: voice_output.speak(error_msg)
            elif VOICE_SETTINGS.get("tts_provider") == "system":
                # Assuming system voice might be settable by name if we had a list like available_system_voices
                # For now, let's say system voice changing via this command is not fully supported yet unless an exact name match is found.
                # You could extend this to iterate through available_system_voices keys if they are simple names.
                VOICE_SETTINGS["system_voice"] = new_voice_name # Directly set, user needs to know exact name
                save_settings()
                feedback_msg = f"System TTS voice set to '{new_voice_name}'. Effectiveness depends on system support for this name."
                print(f"\nAssistant: {feedback_msg}")
                if VOICE_SETTINGS["enabled"]: voice_output.speak(feedback_msg)
            else:
                print("\nAssistant: TTS provider is not set to OpenAI or System, cannot change voice model via this command.")
        else:
            print("\nAssistant: Usage: voice voice <voice_name>")
        return

    if user_input.lower().startswith("voice speed "):
        parts = user_input.split(" ", 2)
        if len(parts) == 3:
            try:
                new_speed = float(parts[2].strip())
                # Assuming OpenAI TTS range 0.25 to 4.0. Adjust if other TTS providers have different ranges.
                if 0.25 <= new_speed <= 4.0:
                    VOICE_SETTINGS["speed"] = new_speed
                    save_settings()
                    feedback_msg = f"TTS speed changed to {new_speed}."
                    print(f"\nAssistant: {feedback_msg}")
                    if VOICE_SETTINGS["enabled"]: voice_output.speak(feedback_msg)
                else:
                    error_msg = "Invalid speed value. Please enter a number between 0.25 and 4.0."
                    print(f"\nAssistant: {error_msg}")
                    if VOICE_SETTINGS["enabled"]: voice_output.speak(error_msg)
            except ValueError:
                error_msg = "Invalid speed value. Please enter a number."
                print(f"\nAssistant: {error_msg}")
                if VOICE_SETTINGS["enabled"]: voice_output.speak(error_msg)
        else:
            print("\nAssistant: Usage: voice speed <value>")
        return

    # Check for help command
    if user_input.lower() == "help":
        print(HELP_TEXT)
        if VOICE_SETTINGS["enabled"]:
            voice_output.speak(HELP_TEXT)
        return
    
    # Check if the input is a file path and an image
    try:
        debug_print(f"Input handler received: {user_input!r}")
        # Normalize path (e.g., remove surrounding quotes if dragged from some terminals)
        normalized_input = user_input.strip('\'"')
        debug_print(f"Normalized input: {normalized_input!r}")
        
        is_file = os.path.isfile(normalized_input)
        exists = os.path.exists(normalized_input)
        debug_print(f"Path exists: {exists}, Is file: {is_file}")

        if exists and is_file:
            debug_print(f"Path is an existing file: {normalized_input!r}")
            # Check if it's a supported image type
            supported_extensions = ('.png', '.jpeg', '.jpg', '.gif', '.webp')
            is_image = normalized_input.lower().endswith(supported_extensions)
            debug_print(f"Is image type: {is_image}")

            if is_image:
                debug_print(f"Input detected as image file path: {normalized_input}") # This is the conditional one
                user_input = f"Analyze this image: {normalized_input}"
                debug_print(f"Transformed user_input for MasterAgent: {user_input!r}")
            else:
                debug_print(f"Input is a file, but not a recognized image type: {normalized_input}")
        elif '/' in user_input or '\\\\' in user_input: 
            debug_print(f"Input looks like a path but does not exist as a file or is not a file: {user_input!r}")
            pass
        else:
            debug_print(f"Input does not appear to be a file path: {user_input!r}")

    except Exception as e:
        debug_print(f"Error during file path check: {e}")
        # Proceed with original input if error in path checking

    # Process query
    debug_print(f"Final user_input to MasterAgent.process: {user_input!r}")
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
    
    debug_print(f"Attempting to load .env file from: {env_path}")
    # Load .env, override existing env vars if any
    loaded_successfully = load_dotenv(dotenv_path=env_path, override=True, verbose=False)
    debug_print(f"load_dotenv successful: {loaded_successfully}")

    # Argument parsing for LLM provider
    parser = argparse.ArgumentParser(description="Run the AI Assistant with a specified LLM provider.")
    parser.add_argument(
        "--llm",
        type=str,
        choices=["openai"],
        default="openai",
        help="(Deprecated) Only the OpenAI provider is available."
    )
    parser.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        help="Enable verbose debug logging."
    )
    parser.add_argument(
        "--no-debug",
        dest="debug",
        action="store_false",
        help="Disable verbose debug logging."
    )
    parser.set_defaults(debug=False)
    args = parser.parse_args()

    # Update settings based on the command-line argument
    LLM_PROVIDER_SETTINGS["default_provider"] = args.llm
    SYSTEM_SETTINGS["debug_mode"] = args.debug
    save_settings() # Save the potentially updated setting
    print("[INFO] Using LLM Provider: OPENAI")
    if args.debug:
        print("[INFO] Debug logging enabled.")

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
        debug_print("Main loop ended. Shutting down services.")
        voice_output.shutdown() # Ensure voice output is shutdown cleanly

if __name__ == "__main__":
    main() 
