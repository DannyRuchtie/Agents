"""Voice output module using OpenAI Text-to-Speech and pygame for playback."""

import os
import sys
import select
import tempfile
import threading
import queue
from pathlib import Path
import pygame # For audio playback
from openai import OpenAI # For TTS API
import time
from typing import Optional

from config.settings import VOICE_SETTINGS, SYSTEM_SETTINGS, is_debug_mode, debug_print
from config.openai_config import get_client # To get the configured OpenAI client

def check_input():
    """Check for input without blocking."""
    if select.select([sys.stdin], [], [], 0.0)[0]:
        return input().strip()
    return None

class VoiceOutput:
    """Handles Text-to-Speech using OpenAI and plays audio via pygame."""
    
    def __init__(self):
        self.client: Optional[OpenAI] = get_client() # Get the shared OpenAI client instance
        self.temp_dir = Path(SYSTEM_SETTINGS.get("app_path", tempfile.gettempdir())) / "temp_audio"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        self.speaking_flag = threading.Event() # Used to signal active speech
        self.stop_flag = threading.Event()     # Used to signal interruption
        self.audio_queue = queue.Queue()
        self.worker_thread = None
        
        try:
            pygame.mixer.init()
            debug_print("Pygame mixer initialized for audio playback.")
        except Exception as e:
            debug_print(f"Error initializing pygame mixer: {e}. Voice output will be silent.")
            self.client = None # Disable if pygame fails

        if self.client:
            self.worker_thread = threading.Thread(target=self._process_audio_queue, daemon=True)
            self.worker_thread.start()
            debug_print("VoiceOutput initialized with OpenAI TTS provider.")
        else:
            debug_print("OpenAI client not available or pygame mixer failed. VoiceOutput disabled.")

    def _generate_speech_file(self, text: str, temp_file_path: Path) -> bool:
        if not self.client:
            return False
        try:
            response = self.client.audio.speech.create(
                model=VOICE_SETTINGS.get("openai_model", "tts-1"),
                voice=VOICE_SETTINGS.get("openai_voice", "alloy"),
                input=text,
                speed=VOICE_SETTINGS.get("speed", 1.0)
            )
            response.stream_to_file(str(temp_file_path))
            debug_print(f"Speech audio saved to {temp_file_path}")
            return True
        except Exception as e:
            debug_print(f"Error generating speech with OpenAI TTS: {e}")
            return False

    def _play_audio_file(self, file_path: Path):
        if not pygame.mixer.get_init():
            debug_print("Pygame mixer not initialized. Cannot play audio.")
            return

        try:
            pygame.mixer.music.load(str(file_path))
            pygame.mixer.music.play()
            self.speaking_flag.set() # Indicate speech has started
            self.stop_flag.clear()   # Clear any previous stop signal
            
            while pygame.mixer.music.get_busy():
                if self.stop_flag.is_set():
                    pygame.mixer.music.stop()
                    debug_print("Playback stopped by user/system.")
                    break
                time.sleep(0.1) # Check for stop signal periodically
        except Exception as e:
            debug_print(f"Error playing audio file {file_path}: {e}")
        finally:
            self.speaking_flag.clear() # Indicate speech has finished or been stopped
            # Clean up the temporary file
            try:
                if file_path.exists():
                    os.remove(file_path)
                    debug_print(f"Temporary audio file {file_path} removed.")
            except Exception as e:
                debug_print(f"Error removing temporary audio file {file_path}: {e}")

    def _process_audio_queue(self):
        while True:
            try:
                text_to_speak = self.audio_queue.get(timeout=1) # Wait for an item
                if text_to_speak is None: # Signal to exit thread
                    break
                
                if self.speaking_flag.is_set(): # If already speaking, wait or discard?
                    debug_print("Audio queue: Already speaking, waiting for current speech to finish.")
                    self.speaking_flag.wait() # Wait for the current speech to complete

                # Ensure stop flag is clear before starting new speech
                self.stop_flag.clear()

                temp_file_path = self.temp_dir / f"speech_{int(time.time() * 1000)}.mp3"
                if self._generate_speech_file(text_to_speak, temp_file_path):
                    self._play_audio_file(temp_file_path)
                
                self.audio_queue.task_done()
            except queue.Empty:
                continue # No item in queue, loop and wait again
            except Exception as e:
                debug_print(f"Error in audio processing worker: {e}")
                # Ensure task_done is called even on error to prevent deadlocks if item was dequeued
                if 'text_to_speak' in locals(): 
                    self.audio_queue.task_done()

    def speak(self, text: str):
        if not VOICE_SETTINGS.get("enabled", False) or not self.client or not pygame.mixer.get_init():
            debug_print("Voice output is disabled, OpenAI client not configured, or pygame mixer not ready.")
            return
        
        # Clear previous stop signals before queuing new text
        # self.stop_speaking() # This might be too aggressive if called before queueing
        self.audio_queue.put(text)
        debug_print(f"Queued for speech: '{text[:50]}...'")

    def stop_speaking(self):
        debug_print("Stop speaking called.")
        self.stop_flag.set() # Signal the playback loop to stop
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            debug_print("Pygame music explicitly stopped.")
        # Clearing the queue might be an option if desired, but could lose queued speech.
        # For now, just stop current and let worker pick up next if any.

    def shutdown(self):
        debug_print("Shutting down VoiceOutput.")
        if self.worker_thread and self.worker_thread.is_alive():
            self.audio_queue.put(None)  # Signal worker to exit
            self.worker_thread.join(timeout=2) # Wait for worker to finish
        if pygame.mixer.get_init():
            pygame.mixer.quit()
            debug_print("Pygame mixer quit.")

# Global instance
voice_output = VoiceOutput()

# Example usage (for testing directly if needed)
if __name__ == '__main__':
    print("VoiceOutput Test Mode")
    # Ensure settings are loaded if run directly (though typically handled by main app import)
    from config.settings import load_settings
    load_settings()
    VOICE_SETTINGS["enabled"] = True # Enable for testing
    SYSTEM_SETTINGS["debug_mode"] = True
    
    # Reinitialize with debug settings if needed, or assume it's already done
    # test_voice = VoiceOutput() # Creates a new instance for test
    global voice_output
    if voice_output: # if global one exists and failed init, re-init might be needed
        voice_output.shutdown()
    voice_output = VoiceOutput() # re-init the global one
    VOICE_SETTINGS["enabled"] = True # Ensure enabled after re-init


    if not voice_output.client or not pygame.mixer.get_init():
        print("Cannot run test: VoiceOutput not properly initialized (OpenAI client or Pygame issue).")
        sys.exit(1)

    print("Testing voice output. Say 'hello world', then 'this is a longer test sentence'.")
    print("Try typing 'stop' in the console during speech to test interruption.")
    
    voice_output.speak("Hello world!")
    time.sleep(1) # Give a moment before queuing next, avoid race condition on very fast speak calls
    voice_output.speak("This is a longer test sentence, check if it plays correctly and can be interrupted.")

    # Keep alive for testing interruption and queued playback
    try:
        while voice_output.audio_queue.unfinished_tasks > 0 or voice_output.speaking_flag.is_set():
            # Check for manual stop input (simplified for test)
            # In a real app, input handling would be more robust
            # For this test, you might need to manually stop the python script (Ctrl+C)
            # or rely on the natural end of speech.
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                line = sys.stdin.readline()
                if 'stop' in line:
                    print("User typed stop, attempting to stop speech.")
                    voice_output.stop_speaking()
            time.sleep(0.2)
        print("All queued audio processed or current speech finished.")
    except KeyboardInterrupt:
        print("Test interrupted by user.")
    finally:
        print("Cleaning up voice output...")
        voice_output.shutdown()
        print("Test finished.") 