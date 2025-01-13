"""Voice output module using kokoro-onnx for text-to-speech."""

import os
import subprocess
import tempfile
from pathlib import Path
import soundfile as sf
from kokoro_onnx import Kokoro

from config.settings import VOICE_SETTINGS, is_debug_mode, debug_print

class VoiceOutput:
    """Voice output class using kokoro-onnx TTS."""
    
    def __init__(self):
        """Initialize voice output with kokoro TTS."""
        self.current_process = None
        self.temp_dir = tempfile.mkdtemp()
        
        # Initialize kokoro TTS
        model_path = Path("models/kokoro-v0_19.onnx")
        voices_path = Path("models/voices.json")
        
        if not model_path.exists() or not voices_path.exists():
            raise RuntimeError("Required model files not found. Please download kokoro-v0_19.onnx and voices.json")
            
        self.tts = Kokoro(str(model_path), str(voices_path))
        debug_print("✓ Voice output system initialized with kokoro-onnx")
        
    def stop_speaking(self):
        """Stop current playback if any."""
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
            
            # Play audio using system player
            debug_print("Playing audio...")
            self.current_process = subprocess.Popen(["afplay", temp_path])
            self.current_process.wait()
            
            # Cleanup
            os.remove(temp_path)
            debug_print("Playback complete, temporary file cleaned up")
            
        except Exception as e:
            debug_print(f"Error generating/playing speech: {str(e)}")
            raise

voice_output = VoiceOutput() 