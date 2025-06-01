"""Main module for the multi-agent chat interface."""
import asyncio
import os
import sys
import select
import threading
import argparse
from pathlib import Path
from typing import Optional, List, Dict
from dotenv import load_dotenv
import queue

from agents.master_agent import MasterAgent
from agents.memory_agent import MemoryAgent
from agents.search_agent import SearchAgent
from agents.writer_agent import WriterAgent
from agents.code_agent import CodeAgent
from agents.scanner_agent import ScannerAgent
from agents.vision_agent import VisionAgent
from agents.learning_agent import LearningAgent
from utils.voice import voice_output
from utils.stt import get_stt_instance, reset_stt_instance

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
    debug_print,
    LLM_PROVIDER_SETTINGS
)

# --- STT Instance and Command Queue ---
stt_command_queue = queue.Queue() # Queue for commands from STT wake word
stt_service = None

def handle_transcribed_command(text: str):
    """Callback for STT service to put transcribed commands onto a queue."""
    if text:
        debug_print(f"[Main] Wake word command received via callback: '{text}'")
        stt_command_queue.put(text)

def initialize_stt_service():
    global stt_service
    if VOICE_SETTINGS.get("stt_enabled", False) or VOICE_SETTINGS.get("wakeword_enabled", False):
        if is_debug_mode():
            debug_print("Initializing STT service...")
        stt_service = get_stt_instance(wake_word_callback=handle_transcribed_command)
        if VOICE_SETTINGS.get("wakeword_enabled", False) and stt_service and stt_service.porcupine:
            stt_service.start_wake_word_listening()
        elif VOICE_SETTINGS.get("wakeword_enabled", False):
            print("[Main Warning] Wake word is enabled in settings, but Porcupine failed to initialize in STT service.")
    else:
        if is_debug_mode():
            debug_print("STT/Wakeword not enabled, STT service not initialized by default.")

def check_input() -> Optional[str]:
    """Check for user input from stdin or STT command queue without blocking."""
    # Check stdin first
    try:
        if sys.stdin in select.select([sys.stdin], [], [], 0.0)[0]:
            line = sys.stdin.readline().strip()
            if line: # Check if the line is not empty
                return line
    except Exception as e:
        debug_print(f"Error reading from stdin: {e}")
        pass # Ignore errors like EBADF if stdin is closed
    
    # Then check STT command queue
    try:
        return stt_command_queue.get_nowait()
    except queue.Empty:
        return None

async def process_input(master_agent: MasterAgent, user_input: str):
    """Process user input and handle responses."""
    global stt_service # Moved global declaration to the top of the function
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

    # STT control commands
    if user_input.lower() == "speech on" or user_input.lower() == "speech enable":
        if not VOICE_SETTINGS.get("stt_enabled", False):
            VOICE_SETTINGS["stt_enabled"] = True # General STT flag
            print("\nAssistant: Speech input (STT) functionally enabled.")
            # Wake word specific enabling/disabling is separate
        
        if VOICE_SETTINGS.get("wakeword_enabled", False):
            if stt_service is None:
                stt_service = get_stt_instance(wake_word_callback=handle_transcribed_command)
            if stt_service and stt_service.porcupine:
                stt_service.start_wake_word_listening() # This also prints status
                if VOICE_SETTINGS["enabled"]: voice_output.speak("Wake word listening started.")
            elif stt_service:
                print("\nAssistant: Wake word enabled in settings, but Porcupine model failed to load. Wake word listening not started.")
                if VOICE_SETTINGS["enabled"]: voice_output.speak("Wake word model failed.")
            else: # Should not happen if stt_service was initialized
                print("\nAssistant: STT Service not available for wake word.")
        else: # Wake word not enabled, but speech on means STT features are generally on
            print("\nAssistant: General speech input is on. Use 'listen' command or enable 'wakeword_enabled' in settings for continuous listening.")
            if stt_service is None: # Ensure STT (Whisper) is loaded for 'listen'
                 stt_service = get_stt_instance(wake_word_callback=handle_transcribed_command)
                 if not stt_service.whisper_model:
                     print("\nAssistant: Whisper model failed to load. The 'listen' command may not work.")

        save_settings()
        return

    if user_input.lower() == "speech off" or user_input.lower() == "speech disable":
        # This command will primarily stop wake word. General STT (for 'listen') remains technically enabled by VOICE_SETTINGS["stt_enabled"]
        # To fully disable STT including 'listen', one would set VOICE_SETTINGS["stt_enabled"] = False and VOICE_SETTINGS["wakeword_enabled"] = False
        if stt_service and VOICE_SETTINGS.get("wakeword_enabled", False):
            stt_service.stop_wake_word_listening()
            # VOICE_SETTINGS["wakeword_enabled"] = False # Optionally turn off wake word in settings too
            if VOICE_SETTINGS["enabled"]: voice_output.speak("Wake word listening stopped.")
        else:
            print("\nAssistant: Wake word listening is not active or not enabled in settings.")
        
        # If you want 'speech off' to also disable the stt_enabled flag for the 'listen' command:
        # VOICE_SETTINGS["stt_enabled"] = False 
        # print("\nAssistant: All speech input (including 'listen' command) disabled.")

        save_settings()
        return

    if user_input.lower() == "speech status": 
        stt_enabled_flag = VOICE_SETTINGS.get("stt_enabled", False)
        ww_enabled_flag = VOICE_SETTINGS.get("wakeword_enabled", False)
        stt_provider = VOICE_SETTINGS.get("stt_provider", "local_whisper")
        
        if stt_provider == "local_whisper":
            stt_model_detail = f"Local Whisper Model: {VOICE_SETTINGS.get('whisper_model', 'N/A')}"
        elif stt_provider == "openai_api":
            stt_model_detail = f"OpenAI API Model: {VOICE_SETTINGS.get('openai_stt_model', 'N/A')}"
        else:
            stt_model_detail = "STT Model: Unknown provider"
            
        ww_keywords = VOICE_SETTINGS.get("picovoice_keywords", []) or VOICE_SETTINGS.get("picovoice_keyword_paths", [])
        
        status_parts = []
        status_parts.append(f"General STT: {'Enabled' if stt_enabled_flag else 'Disabled'}")
        status_parts.append(f"STT Provider: {stt_provider.replace('_', ' ').title()}")
        status_parts.append(stt_model_detail)
        status_parts.append(f"Wake Word: {'Enabled' if ww_enabled_flag else 'Disabled'} (Porcupine keywords: {ww_keywords})")
        
        if ww_enabled_flag and stt_service and stt_service.is_listening_for_wake_word:
            status_parts.append("Wake word actively listening.")
        elif ww_enabled_flag and stt_service and not stt_service.porcupine:
             status_parts.append("(Porcupine engine not loaded/failed)")
        elif ww_enabled_flag and not (stt_service and stt_service.is_listening_for_wake_word):
            status_parts.append("(Wake word not actively listening - try 'speech on')")
            
        stt_msg = "\n".join(status_parts)
        print(f"\nAssistant:\n{stt_msg}")
        if VOICE_SETTINGS["enabled"]:
            voice_output.speak(f"Speech input status: General STT is {'Enabled' if stt_enabled_flag else 'Disabled'}. Provider is {stt_provider}. Wake word is {'Enabled' if ww_enabled_flag else 'Disabled'}.")
        return

    if user_input.lower().startswith("speech provider "):
        parts = user_input.split(" ", 2)
        if len(parts) == 3:
            new_provider = parts[2].strip().lower()
            if new_provider in ["local_whisper", "openai_api"]:
                VOICE_SETTINGS["stt_provider"] = new_provider
                save_settings()
                feedback_msg = f"STT provider changed to {new_provider.replace('_', ' ').title()}."
                print(f"\nAssistant: {feedback_msg}")
                if VOICE_SETTINGS["enabled"]: voice_output.speak(feedback_msg)
                
                # Re-initialize STT service with the new provider setting
                if stt_service:
                    stt_service.release_resources() # Release old resources
                reset_stt_instance() # Reset the global instance in stt.py
                # Create a new instance with potentially new provider logic in SpeechToText __init__
                stt_service = get_stt_instance(wake_word_callback=handle_transcribed_command)
                # If wake word was on, try to restart it with the new STT service instanceclear
                
                if VOICE_SETTINGS.get("wakeword_enabled", False) and stt_service and stt_service.porcupine:
                    stt_service.start_wake_word_listening()
                elif VOICE_SETTINGS.get("wakeword_enabled", False):
                     print("[Main Warning] Wake word enabled, but Porcupine may not be available for the new STT provider or failed to init.")

            else:
                print("\nAssistant: Invalid STT provider. Use 'local_whisper' or 'openai_api'.")
        else:
            print("\nAssistant: Usage: speech provider <local_whisper|openai_api>")
        return

    if user_input.lower().startswith("speech model "):
        parts = user_input.split(" ", 2)
        if len(parts) == 3:
            new_model = parts[2].strip()
            # Basic validation, more robust validation could check against Whisper's known models
            if new_model and not new_model.isspace():
                VOICE_SETTINGS["whisper_model"] = new_model
                save_settings()
                # Re-initialize STT service with the new model if it's enabled
                if VOICE_SETTINGS.get("stt_enabled", False) and stt_service:
                    print(f"\nAssistant: Attempting to change STT model to '{new_model}'. Re-initializing...")
                    stt_service._load_model() # This will load the new model
                    if stt_service.model:
                         confirmation_msg = f"STT model changed to {new_model}."
                         print(f"Assistant: {confirmation_msg}")
                         if VOICE_SETTINGS["enabled"]: voice_output.speak(confirmation_msg)
                    else:
                        error_msg = f"Failed to load STT model {new_model}. Previous model might still be active or STT is unusable."
                        print(f"Assistant: {error_msg}")
                        if VOICE_SETTINGS["enabled"]: voice_output.speak(error_msg)
                else: # STT not enabled, just save setting
                     print(f"\nAssistant: STT model preference set to '{new_model}'. Enable STT to use it.")
            else:
                print("\nAssistant: Invalid STT model name provided.")
        else:
            print("\nAssistant: Usage: speech model <model_name_or_path>")
        return
        
    # New "listen" command for one-time STT
    if user_input.lower() == "listen":
        if not VOICE_SETTINGS.get("stt_enabled", False):
            print("\nAssistant: STT is not enabled. Type 'speech on' and ensure 'stt_enabled' is true in settings.")
            return
        if stt_service is None:
            stt_service = get_stt_instance(wake_word_callback=handle_transcribed_command)

        if stt_service and stt_service.whisper_model:
            # Ensure wake word is not interfering, or use a flag if STT service manages this
            if stt_service.is_listening_for_wake_word:
                print("\nAssistant: Wake word is active. 'listen' command temporarily pauses it if needed by STT service design.")
                # Ideally, stt_service would handle this pause/resume internally if direct listen is called.
                # For now, we assume stt_service.listen_and_transcribe_once() can coexist or is preferred.
            
            transcribed_text = stt_service.listen_and_transcribe_once() # Call the renamed method
            if transcribed_text:
                # The stt_service.listen_and_transcribe() already prints the transcribed text.
                # No need for: print(f"You (voice): {transcribed_text}") 
                user_input = transcribed_text # This will be processed by MasterAgent below
            else:
                # No valid transcription, or STT failed. Don't proceed to MasterAgent.
                # Ensure prompt is shown for next manual input.
                # This return will go back to chat_loop, which will set prompt_shown = False.
                return 
        elif not VOICE_SETTINGS.get("stt_enabled", False):
            print("\nAssistant: STT is not enabled. Type 'speech on' to enable it.")
            return
        else: # STT enabled but model not loaded
            print("\nAssistant: STT is enabled but the Whisper model is not loaded. Cannot listen.")
            return

    # Check for help command
    if user_input.lower() == "help":
        help_text = """\nAvailable Commands:
Agent Management:
- list agents - Show all available agents and their status
- enable agent [name] - Enable a specific agent
- disable agent [name] - Disable a specific agent

Voice Output (TTS):
- voice status - Show voice output status
- voice on/enable - Enable voice output
- voice off/disable - Disable voice output
- voice stop/stop - Stop current speech
- voice voice [name] - Change voice
- voice speed [value] - Change voice speed (0.5-2.0)

Speech Input (STT) & Wake Word:
- speech on/enable - Enables general STT. If wake word is configured and enabled in settings, starts wake word listening.
- speech off/disable - Disables wake word listening if active. General STT (for 'listen' command) might remain enabled based on settings.
- speech status - Show STT and wake word status, including loaded models/keywords.
- speech provider <local_whisper|openai_api> - Change STT provider.
- speech model <model_name> - Change STT model (for local Whisper: tiny.en, base.en; for OpenAI: whisper-1).
- listen - Activate a one-time voice input using the configured STT provider.
  (Note: Configure wake word keywords, Picovoice AccessKey, and enable it in config/settings.py or .json)

General:
- help - Show this help message
- exit - Exit the assistant
"""
        print(help_text)
        if VOICE_SETTINGS["enabled"]:
            voice_output.speak(help_text)
        return
    
    # Check if the input is a file path and an image
    try:
        if is_debug_mode():
            print(f"[FORCE_PRINT_MAIN] Original user_input: '{user_input}'")
        # Normalize path (e.g., remove surrounding quotes if dragged from some terminals)
        normalized_input = user_input.strip('\'"')
        if is_debug_mode():
            print(f"[FORCE_PRINT_MAIN] Normalized input: '{normalized_input}'")
        
        is_file = os.path.isfile(normalized_input)
        exists = os.path.exists(normalized_input)
        if is_debug_mode():
            print(f"[FORCE_PRINT_MAIN] Path exists: {exists}, Is file: {is_file}")

        if exists and is_file:
            if is_debug_mode():
                print(f"[FORCE_PRINT_MAIN] Path is an existing file: '{normalized_input}'")
            # Check if it's a supported image type
            supported_extensions = ('.png', '.jpeg', '.jpg', '.gif', '.webp')
            is_image = normalized_input.lower().endswith(supported_extensions)
            if is_debug_mode():
                print(f"[FORCE_PRINT_MAIN] Is image type: {is_image}")

            if is_image:
                if is_debug_mode():
                    debug_print(f"Input detected as image file path: {normalized_input}")
                if is_debug_mode():
                    print(f"[FORCE_PRINT_MAIN] Confirmed image file. Original query: '{user_input}'")
                user_input = f"Analyze this image: {normalized_input}"
                if is_debug_mode():
                    print(f"[FORCE_PRINT_MAIN] Transformed user_input for MasterAgent: '{user_input}'")
            else:
                if is_debug_mode():
                    debug_print(f"Input is a file, but not a recognized image type: {normalized_input}")
                if is_debug_mode():
                    print(f"[FORCE_PRINT_MAIN] File exists, but not a supported image type: '{normalized_input}'")
        elif '/' in user_input or '\\\\' in user_input: 
            if is_debug_mode():
                print(f"[FORCE_PRINT_MAIN] Input '{user_input}' looks like a path but does not exist as a file or is not a file.")
            pass
        else:
            if is_debug_mode():
                print(f"[FORCE_PRINT_MAIN] Input '{user_input}' does not appear to be a file path.")

    except Exception as e:
        if is_debug_mode():
            debug_print(f"Error during file path check: {e}")
        if is_debug_mode():
            print(f"[FORCE_PRINT_MAIN] Exception during file path check: {e}")
        # Proceed with original input if error in path checking

    # Process query
    if is_debug_mode():
        print(f"[FORCE_PRINT_MAIN] Final user_input to MasterAgent.process: '{user_input}'")
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
    
    if is_debug_mode():
        debug_print("Settings loaded successfully")
    # Load .env, override existing env vars if any, and be verbose if file not found
    loaded_successfully = load_dotenv(dotenv_path=env_path, override=True, verbose=is_debug_mode())
    if is_debug_mode():
        debug_print(f"load_dotenv successful: {loaded_successfully}")

    # Argument parsing for LLM provider
    parser = argparse.ArgumentParser(description="Run the AI Assistant with a specified LLM provider.")
    parser.add_argument(
        "--llm",
        type=str,
        choices=["openai", "ollama"],
        default=LLM_PROVIDER_SETTINGS["default_provider"],
        help="Specify the LLM provider to use (openai or ollama). Defaults to ollama."
    )
    args = parser.parse_args()

    # Update the setting based on the command-line argument
    LLM_PROVIDER_SETTINGS["default_provider"] = args.llm
    save_settings() # Save the potentially updated setting
    if is_debug_mode():
        debug_print(f"Using LLM Provider: {args.llm.upper()}")

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
        # Initialize STT service (which might start wake word listening)
        initialize_stt_service()
        asyncio.run(chat_loop())
    finally:
        if is_debug_mode():
            debug_print("Main loop ended. Shutting down services.")
        if stt_service:
            stt_service.release_resources()
            if is_debug_mode():
                debug_print("STT service resources released.")
        voice_output.shutdown() # Ensure voice output is shutdown cleanly

if __name__ == "__main__":
    main() 