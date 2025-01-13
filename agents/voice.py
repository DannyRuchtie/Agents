"""Voice module for text-to-speech functionality."""
import os
import tempfile
import asyncio
from pathlib import Path
from openai import OpenAI
from config.settings import (
    VOICE_SETTINGS,
    is_voice_enabled,
    get_voice_info,
    is_debug_mode,
    debug_print
)

class VoiceOutput:
    """Handles text-to-speech conversion using OpenAI's API."""
    
    def __init__(self):
        """Initialize the voice output system."""
        self.client = OpenAI()
        self.temp_dir = Path(tempfile.gettempdir()) / "agent_voice"
        self.temp_dir.mkdir(exist_ok=True)
        self.current_process = None
        print("✓ Voice output system initialized")
        
    def stop_speaking(self):
        """Stop the current speech playback."""
        if self.current_process:
            try:
                debug_print("Stopping current playback...")
                # On macOS, kill the afplay process
                os.kill(self.current_process.pid, 9)
                self.current_process = None
                debug_print("✓ Playback stopped")
            except:
                pass
        
    async def speak(self, text: str) -> None:
        """Convert text to speech and play it."""
        if not is_voice_enabled():
            debug_print("Voice output is disabled")
            return
            
        debug_print("\n=== Voice Output ===")
        debug_print(f"Text to speak: {text[:50]}...")
            
        # Stop any current playback
        self.stop_speaking()
        
        temp_file = None
        try:
            # Get current voice settings
            voice_info = get_voice_info()
            voice = voice_info["current_voice"]
            speed = voice_info["current_speed"]
            debug_print(f"Using voice: {voice}, speed: {speed}")
            
            # Create a temporary file for the audio
            temp_file = self.temp_dir / f"speech_{hash(text)}.mp3"
            debug_print(f"Creating audio file: {temp_file}")
            
            # Generate speech using OpenAI's API
            debug_print("Generating speech with OpenAI API...")
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=text,
                    speed=speed
                )
            )
            
            # Save to temporary file
            debug_print("Saving audio file...")
            response.stream_to_file(str(temp_file))
            
            if not temp_file.exists():
                raise Exception("Failed to create audio file")
            
            debug_print(f"Audio file created: {temp_file.stat().st_size} bytes")
            
            # Play the audio using system command (afplay on macOS)
            debug_print("Playing audio...")
            self.current_process = await asyncio.create_subprocess_exec(
                'afplay', str(temp_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for playback to complete or interruption
            try:
                await self.current_process.communicate()
                debug_print("✓ Playback completed")
            except Exception as e:
                debug_print(f"Playback interrupted: {e}")
            finally:
                self.current_process = None
            
            # Clean up
            if temp_file.exists():
                temp_file.unlink()
                debug_print("✓ Temporary file cleaned up")
            
        except Exception as e:
            debug_print(f"❌ Error in voice output: {str(e)}")
            # Clean up on error
            if temp_file and temp_file.exists():
                temp_file.unlink()
                debug_print("✓ Cleaned up temporary file after error")
        
        debug_print("=== Voice Output Complete ===\n")

voice_output = VoiceOutput() 