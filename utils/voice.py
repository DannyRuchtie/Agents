"""Voice output module using kokoro-onnx for text-to-speech."""

import os
import sys
import select
import subprocess
import tempfile
import threading
from pathlib import Path
import soundfile as sf
from kokoro_onnx import Kokoro

from config.settings import VOICE_SETTINGS, is_debug_mode, debug_print

def check_input():
    """Check for input without blocking."""
    if select.select([sys.stdin], [], [], 0.0)[0]:
        return input().strip()
    return None

class VoiceOutput:
    """Voice output class using kokoro-onnx TTS."""
    
    def __init__(self):
        """Initialize voice output with kokoro TTS."""
        self.current_process = None
        self.temp_dir = tempfile.mkdtemp()
        self.speaking = False
        
        # Initialize kokoro TTS
        model_path = Path("models/kokoro-v0_19.onnx")
        voices_path = Path("models/voices.json")
        
        if not model_path.exists() or not voices_path.exists():
            raise RuntimeError("Required model files not found. Please download kokoro-v0_19.onnx and voices.json")
            
        self.tts = Kokoro(str(model_path), str(voices_path))
        debug_print("✓ Voice output system initialized with kokoro-onnx")
        
    def stop_speaking(self):
        """Stop current playback if any."""
        self.speaking = False
        if self.current_process and self.current_process.poll() is None:
            debug_print("Stopping current playback...")
            self.current_process.terminate()
            self.current_process.wait()
            
    def speak(self, text: str):
        """Convert text to speech and play it."""
        if not VOICE_SETTINGS["enabled"]:
            debug_print("Voice output is disabled")
            return
            
        try:
            debug_print(f"Generating speech for: {text}")
            debug_print(f"Using voice: {VOICE_SETTINGS['voice']}")
            
            # Generate speech using kokoro
            audio = self.tts.create(text, voice=VOICE_SETTINGS['voice'])
            
            # Create temporary WAV file
            temp_path = os.path.join(self.temp_dir, "temp_speech.wav")
            
            # Ensure audio is in the correct format (mono, float32)
            if isinstance(audio, tuple):
                audio = audio[0]  # Take first channel if stereo
            
            # Write audio data
            sf.write(temp_path, audio, 24000, format='WAV', subtype='FLOAT')
            
            debug_print(f"Created audio file: {temp_path}")
            
            # Stop any current playback
            self.stop_speaking()
            
            # Start playback in a separate thread
            self.speaking = True
            thread = threading.Thread(target=self._play_audio, args=(temp_path,))
            thread.start()
            
        except Exception as e:
            debug_print(f"Error generating/playing speech: {str(e)}")
            raise
            
    def _play_audio(self, audio_path: str):
        """Play audio file and check for interruption."""
        try:
            # Start the audio playback
            self.current_process = subprocess.Popen(["afplay", audio_path])
            
            # Check for input while playing
            while self.speaking and self.current_process.poll() is None:
                user_input = check_input()
                if user_input:
                    self.stop_speaking()
                    # Don't print the input here, let main loop handle it
                    break
            
            # Wait for process to finish if not stopped
            if self.current_process.poll() is None:
                self.current_process.wait()
            
            # Cleanup
            os.remove(audio_path)
            debug_print("Playback complete, temporary file cleaned up")
            
        except Exception as e:
            debug_print(f"Error in audio playback: {str(e)}")
            self.speaking = False

voice_output = VoiceOutput() 