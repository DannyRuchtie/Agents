"""Voice output module using kokoro-onnx for text-to-speech."""

import os
import sys
import select
import subprocess
import tempfile
import threading
import queue
from pathlib import Path
import soundfile as sf
# from kokoro_onnx import Kokoro # Commented out

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
        self.audio_queue = queue.Queue()
        self.worker_thread = None
        self.tts = None # Initialize tts to None

        try:
            from kokoro_onnx import Kokoro # Try to import locally
            # Initialize kokoro TTS
            model_path = Path("models/kokoro-v0_19.onnx")
            voices_path = Path("models/voices.json")
            
            if not model_path.exists() or not voices_path.exists():
                debug_print("Required Kokoro model files not found. Voice output disabled.")
                # raise RuntimeError("Required model files not found. Please download kokoro-v0_19.onnx and voices.json") # Don't raise error
            else:
                self.tts = Kokoro(str(model_path), str(voices_path))
                debug_print("✓ Voice output system initialized with kokoro-onnx")
            
            # Start worker thread only if tts is initialized
            if self.tts:
                self.worker_thread = threading.Thread(target=self._process_audio_queue, daemon=True)
                self.worker_thread.start()
            else:
                debug_print("Kokoro TTS not initialized, voice output will be silent.")

        except ImportError:
            debug_print("kokoro_onnx not found. Voice output will be silent.")
            self.tts = None # Ensure tts is None if import fails
        
    def stop_speaking(self):
        """Stop current playback if any."""
        self.speaking = False
        if self.current_process and self.current_process.poll() is None:
            self.current_process.terminate()
            self.current_process.wait()
            
    def speak(self, text: str):
        """Queue text for speech synthesis."""
        if not VOICE_SETTINGS["enabled"] or not self.tts:
            debug_print("Voice output disabled or TTS not initialized.")
            return
            
        # Add to queue and return immediately
        self.audio_queue.put(text)
        
    def _process_audio_queue(self):
        """Background worker to process audio queue."""
        if not self.tts: # Guard against running if tts is not initialized
            return

        while True:
            try:
                # Get next text to process
                text = self.audio_queue.get()
                if text is None:
                    break
                    
                try:
                    # Generate speech using kokoro
                    audio = self.tts.create(text, voice=VOICE_SETTINGS['voice'])
                    
                    # Create temporary WAV file with optimized settings
                    temp_path = os.path.join(self.temp_dir, "temp_speech.wav")
                    
                    # Ensure audio is in the correct format (mono)
                    if isinstance(audio, tuple):
                        audio = audio[0]  # Take first channel if stereo
                    
                    # Write audio data with optimized settings
                    sf.write(temp_path, audio, 24000, format='WAV', subtype='PCM_16')
                    
                    # Play the audio
                    self._play_audio(temp_path)
                    
                except Exception as e:
                    debug_print(f"Error generating/playing speech: {str(e)}")
                    
                finally:
                    self.audio_queue.task_done()
                    
            except queue.Empty:
                continue
                
    def _play_audio(self, audio_path: str):
        """Play audio file and check for interruption."""
        try:
            # Stop any current playback
            self.stop_speaking()
            
            # Start the audio playback
            self.speaking = True
            self.current_process = subprocess.Popen(["afplay", audio_path])
            
            # Check for input while playing
            while self.speaking and self.current_process.poll() is None:
                user_input = check_input()
                if user_input:
                    self.stop_speaking()
                    break
            
            # Wait for process to finish if not stopped
            if self.current_process.poll() is None:
                self.current_process.wait()
            
            # Cleanup
            os.remove(audio_path)
            
        except Exception as e:
            debug_print(f"Error in audio playback: {str(e)}")
            self.speaking = False

voice_output = VoiceOutput() 