"""Main module for the multi-agent chat interface."""
import asyncio
import os
from pathlib import Path
from typing import Optional

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

def main():
    """Run the main chat interface."""
    # Ensure directories exist
    ensure_directories()
    
    print("\nWelcome to the AI Assistant! Type 'help' for commands, 'exit' to quit.\n")
    
    async def chat_loop():
        master_agent = MasterAgent()
        
        while True:
            try:
                # Get user input
                user_input = input("\nYou: ").strip()
                
                # Stop any ongoing speech when new input is received
                voice_output.stop_speaking()
                
                # Handle simple stop command
                if user_input.lower() in ["stop", "voice stop"]:
                    print("\nAssistant: Voice output stopped")
                    continue
                
                # Check for exit command
                if user_input.lower() == "exit":
                    print("\nGoodbye! 👋")
                    break
                
                # Check for help command
                if user_input.lower() == "help":
                    help_text = "\nAvailable Commands:\nAgent Management:\n- list agents - Show all available agents and their status\n- enable agent [name] - Enable a specific agent\n- disable agent [name] - Disable a specific agent\n\nVoice Output:\n- voice status - Show voice output status\n- voice on/enable - Enable voice output\n- voice off/disable - Disable voice output\n- voice stop/stop - Stop current speech\n- voice voice [name] - Change voice\n- voice speed [value] - Change voice speed (0.5-2.0)"
                    print(help_text)
                    if VOICE_SETTINGS["enabled"]:
                        voice_output.speak(help_text)
                    continue
                
                # Process query
                response = await master_agent.process(user_input)
                print(f"\nAssistant: {response}")
                
                # Speak response if voice is enabled
                if VOICE_SETTINGS["enabled"] and not user_input.lower().startswith("voice"):
                    debug_print("Speaking response with voice output")
                    voice_output.speak(response)
            
            except KeyboardInterrupt:
                print("\nGoodbye! 👋")
                break
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                debug_print(error_msg)
                print(f"\n{error_msg}")

    # Run the chat loop
    asyncio.run(chat_loop())

if __name__ == "__main__":
    main() 