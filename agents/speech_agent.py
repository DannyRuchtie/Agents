"""Speech agent for text-to-speech conversion."""
import os
import tempfile
import time
from pathlib import Path
from typing import Optional
import pygame
import openai
import asyncio
from pydub import AudioSegment
import subprocess

from .base_agent import BaseAgent
from config.paths_config import get_path

SPEECH_SYSTEM_PROMPT = """You are a Speech Agent responsible for converting text to natural-sounding speech.
Focus on clear and engaging voice synthesis."""

class SpeechAgent(BaseAgent):
    """Agent for handling text-to-speech conversion."""
    
    # Available voices and their characteristics
    VOICE_PROFILES = {
        "alloy": {"description": "Neutral and balanced", "gender": "neutral"},
        "echo": {"description": "Young and bright", "gender": "female"},
        "fable": {"description": "British and authoritative", "gender": "female"},
        "onyx": {"description": "Deep and powerful", "gender": "male"},
        "nova": {"description": "Energetic and friendly", "gender": "female"},
        "shimmer": {"description": "Clear and expressive", "gender": "female"}
    }
    
    def __init__(self):
        """Initialize the Speech Agent."""
        super().__init__(
            agent_type="speech",
            system_prompt=SPEECH_SYSTEM_PROMPT,
        )
        # Get speech output directory from config
        self.speech_dir = get_path('speech_output')
        # Ensure the directory exists
        self.speech_dir.mkdir(parents=True, exist_ok=True)
        print(f"Speech output directory: {self.speech_dir}")
        
        self.voice = "nova"  # Default to a more energetic voice
        self.speed = 1.0  # Default speed
        self.auto_play = True  # Start with auto-play enabled by default
        
        # Load environment variables from .env file
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("✓ Loaded environment from .env file")
        except Exception as e:
            print(f"❌ Error loading .env file: {str(e)}")
        
        # Initialize OpenAI client with verification
        if 'OPENAI_API_KEY' not in os.environ:
            print("\n❌ OpenAI API key not found!")
            print("Please check your .env file contains:")
            print("OPENAI_API_KEY=your_key_here")
            self.auto_play = False
            return
            
        try:
            from openai import OpenAI
            self.client = OpenAI()
            # Test the API key with a small request
            response = self.client.models.list()
            print("✓ OpenAI API key verified successfully")
        except Exception as e:
            print(f"\n❌ OpenAI API Error: {str(e)}")
            print("\nPlease check your OpenAI API key in .env:")
            if 'OPENAI_API_KEY' in os.environ:
                key = os.environ['OPENAI_API_KEY']
                print(f"1. Key found (starts with: {key[:4]})")
                print(f"2. Key length: {len(key)} characters")
                print("3. Key has required permissions for TTS")
            print("\nMake sure your .env file contains:")
            print("OPENAI_API_KEY=your_key_here")
            self.auto_play = False
            return
            
        # Initialize audio system and run test
        print("\n=== Testing Speech System ===")
        try:
            # Initialize audio
            self._initialize_audio()
            
            # Run test beep
            print("Testing audio playback...")
            import numpy as np
            duration = 0.1  # seconds
            frequency = 440  # Hz
            sample_rate = 44100
            t = np.linspace(0, duration, int(sample_rate * duration))
            samples = np.sin(2 * np.pi * frequency * t)
            samples = (samples * 32767).astype(np.int16)
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                import wave
                with wave.open(temp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(samples.tobytes())
                
                pygame.mixer.music.load(temp_file.name)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(10)
                pygame.mixer.music.unload()
                os.unlink(temp_file.name)
            print("✓ Audio system initialized and tested successfully")
            
        except Exception as e:
            print(f"❌ Error initializing audio: {str(e)}")
            print("Please check:")
            print("1. Your audio device is connected")
            print("2. No other application is blocking audio")
            print("3. You have necessary permissions")
            self.auto_play = False
    
    def _initialize_audio(self):
        """Initialize the audio system."""
        try:
            # Clean up any existing mixer
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            
            # Initialize with high quality settings
            pygame.mixer.init(
                frequency=44100,
                size=-16,
                channels=2,
                buffer=4096
            )
            print("🔊 Audio system initialized successfully")
            
        except Exception as e:
            print(f"❌ Error initializing audio: {str(e)}")
            print("Please check:")
            print("1. Your audio device is connected")
            print("2. No other application is blocking audio")
            print("3. You have necessary permissions")
    
    def enable_speech(self) -> str:
        """Enable speech output."""
        print("\n=== Speech Initialization Debug ===")
        
        # Step 1: Check OpenAI API key
        if 'OPENAI_API_KEY' not in os.environ:
            print("❌ Error: OpenAI API key not found")
            return "Failed to enable speech - OpenAI API key not found"
            
        print(f"✓ Found OpenAI API key (starts with: {os.environ['OPENAI_API_KEY'][:4]})")
        
        # Step 2: Initialize OpenAI client
        try:
            if not hasattr(self, 'client'):
                from openai import OpenAI
                self.client = OpenAI()
            print("✓ OpenAI client initialized")
        except Exception as e:
            print(f"❌ OpenAI client error: {str(e)}")
            return "Failed to enable speech - OpenAI client error"

        # Step 3: Test OpenAI API access
        try:
            print("Testing OpenAI API access...")
            response = self.client.models.list()
            print("✓ OpenAI API key verified")
        except Exception as e:
            print(f"❌ OpenAI API Error: {str(e)}")
            return "Failed to enable speech - Invalid API key"

        # Step 4: Initialize audio system
        try:
            print("Initializing audio system...")
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
            print("✓ Audio system initialized")
        except Exception as e:
            print(f"❌ Audio initialization error: {str(e)}")
            return "Failed to enable speech - Audio system error"

        # Step 5: Test audio with a simple beep
        try:
            print("Testing audio playback...")
            import numpy as np
            duration = 0.1  # seconds
            frequency = 440  # Hz
            sample_rate = 44100
            t = np.linspace(0, duration, int(sample_rate * duration))
            samples = np.sin(2 * np.pi * frequency * t)
            samples = (samples * 32767).astype(np.int16)
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                import wave
                with wave.open(temp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(samples.tobytes())
                
                pygame.mixer.music.load(temp_file.name)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(10)
                pygame.mixer.music.unload()
                os.unlink(temp_file.name)
            print("✓ Audio playback test successful")
        except Exception as e:
            print(f"❌ Audio playback test failed: {str(e)}")
            print("\nTroubleshooting steps:")
            print("1. Check if your system volume is up")
            print("2. Ensure no other apps are blocking audio")
            print("3. Check if your speakers/headphones are connected")
            return "Failed to enable speech - Audio playback error"

        # Step 6: Enable speech
        self.auto_play = True
        print("✓ Speech enabled successfully")
        print("=== Initialization Complete ===\n")
        return "Speech output enabled"
    
    def disable_speech(self) -> str:
        """Disable speech output."""
        self.auto_play = False
        return "🔇 Speech output disabled"
    
    def is_speech_enabled(self) -> bool:
        """Check if speech output is enabled."""
        return self.auto_play
    
    def list_voices(self) -> str:
        """List available voices and their descriptions."""
        voice_list = []
        for name, info in self.VOICE_PROFILES.items():
            current = " (current)" if name == self.voice else ""
            voice_list.append(f"• {name}: {info['description']}{current}")
        return "Available voices:\n" + "\n".join(voice_list)
        
    def set_voice(self, voice: str) -> str:
        """Set the TTS voice to use."""
        voice = voice.lower()
        if voice in self.VOICE_PROFILES:
            self.voice = voice
            return f"🎤 Voice set to: {voice} - {self.VOICE_PROFILES[voice]['description']}"
        return f"❌ Invalid voice. Available voices:\n{self.list_voices()}"
    
    def set_speed(self, speed: float) -> str:
        """Set the speech speed.
        
        Args:
            speed: Speed multiplier (0.5 to 2.0, where 1.0 is normal speed)
        """
        if 0.5 <= speed <= 2.0:
            self.speed = speed
            return f"🏃‍♂️ Speech speed set to {speed}x"
        return "❌ Speed must be between 0.5 (slower) and 2.0 (faster)"
    
    def toggle_autoplay(self) -> str:
        """Toggle auto-play setting."""
        self.auto_play = not self.auto_play
        return f"🔊 Auto-play {'enabled' if self.auto_play else 'disabled'}"
    
    def _play_audio(self, file_path: str) -> None:
        """Play audio file using pygame."""
        print("\n=== Playing Audio ===")
        print(f"1. File path: {file_path}")
        print(f"2. File exists: {os.path.exists(file_path)}")
        print(f"3. File size: {os.path.getsize(file_path)} bytes")
        
        try:
            print("4. Loading audio file...")
            pygame.mixer.music.load(file_path)
            
            print("5. Starting playback...")
            pygame.mixer.music.play()
            
            print("6. Waiting for playback to complete...")
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
                
            print("7. ✓ Playback completed")
            
        except Exception as e:
            print(f"\n❌ Error playing audio: {str(e)}")
            print("\nTroubleshooting steps:")
            print("1. Check if your system volume is up")
            print("2. Check if your speakers/headphones are connected")
            print("3. Try playing another audio file")
            print("4. Check if pygame mixer is initialized:")
            print(f"   Mixer initialized: {pygame.mixer.get_init()}")
            if pygame.mixer.get_init():
                print(f"   Mixer settings: {pygame.mixer.get_init()}")
            raise
            
        print("=== Audio Complete ===\n")
    
    def play_sound(self, sound_type: str) -> None:
        """Play a system sound."""
        # TODO: Implement system sounds for different events
        pass
        
    async def speak(self, text: str) -> None:
        """Speak the given text using text-to-speech."""
        if not text or not self.auto_play:
            print("Speech is disabled or no text to speak")
            return

        print("\n=== Speaking Debug ===")
        print(f"Text to speak: {text}")
        print(f"Speech enabled: {self.auto_play}")
        print(f"Voice: {self.voice}")
        print(f"Speed: {self.speed}")
        
        # Verify OpenAI API key
        if 'OPENAI_API_KEY' not in os.environ:
            print("❌ Error: OpenAI API key not found in environment")
            return
            
        print(f"OpenAI API key found (starts with: {os.environ['OPENAI_API_KEY'][:4]})")
        
        # Use configured speech output directory for debug files
        debug_dir = self.speech_dir / "debug"
        debug_dir.mkdir(exist_ok=True)
        
        # Create temporary files
        mp3_temp = None
        try:
            # Create temp file in speech output directory
            timestamp = int(time.time())
            mp3_path = self.speech_dir / f"speech_{timestamp}.mp3"
            debug_path = debug_dir / f"debug_speech_{timestamp}.mp3"
            
            print(f"Created files:")
            print(f"MP3 path: {mp3_path}")
            print(f"Debug path: {debug_path}")
            
            try:
                # Generate speech
                print("\n1. Calling OpenAI TTS API...")
                print(f"   Model: tts-1")
                print(f"   Voice: {self.voice}")
                print(f"   Speed: {self.speed}")
                print(f"   Text length: {len(text)} characters")
                
                response = await self.client.audio.speech.create(
                    model="tts-1",
                    voice=self.voice,
                    input=text,
                    speed=self.speed
                )
                print("   ✓ TTS API call successful")
                
                # Save MP3 and debug copy
                print("\n2. Saving audio files...")
                response.stream_to_file(str(mp3_path))
                
                # Make a copy for debugging
                import shutil
                shutil.copy2(mp3_path, debug_path)
                
                # Verify files were created
                if not mp3_path.exists():
                    raise Exception("Failed to create MP3 file")
                if not debug_path.exists():
                    raise Exception("Failed to create debug copy")
                    
                mp3_size = mp3_path.stat().st_size
                debug_size = debug_path.stat().st_size
                if mp3_size == 0:
                    raise Exception("Generated MP3 file is empty")
                
                print(f"   ✓ MP3 file created ({mp3_size} bytes)")
                print(f"   ✓ Debug copy created ({debug_size} bytes)")
                
                # Try playing with afplay
                print("\n3. Playing with afplay...")
                process = await asyncio.create_subprocess_exec(
                    'afplay', str(mp3_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Wait for playback to complete
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    print(f"   ❌ Playback error with afplay: {stderr.decode()}")
                    
                    # Try alternative playback with pygame as fallback
                    print("\n4. Trying fallback with pygame...")
                    if not pygame.mixer.get_init():
                        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
                    pygame.mixer.music.load(str(mp3_path))
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        await asyncio.sleep(0.1)
                    print("   ✓ Pygame playback completed")
                else:
                    print("   ✓ Afplay playback completed")
                
                print(f"\nDebug: Audio files saved to:")
                print(f"MP3: {mp3_path}")
                print(f"Debug copy: {debug_path}")
                print("You can test them manually with:")
                print(f"afplay {mp3_path}")
                print(f"afplay {debug_path}")
                
            except Exception as e:
                print(f"\n❌ Error during speech process: {str(e)}")
                print("\nTroubleshooting steps:")
                print("1. Check your OpenAI API key is valid")
                print("2. Ensure your system volume is up")
                print("3. Check if other audio is playing on your system")
                print("4. Try playing the debug files directly:")
                print(f"   {mp3_path}")
                print(f"   {debug_path}")
                raise
                
        finally:
            # Keep both files for debugging
            print("\n5. ✓ Completed")
            print(f"   Files saved at:")
            print(f"   - {mp3_path}")
            print(f"   - {debug_path}")

        print("=== Speaking Complete ===\n")
        
    async def text_to_speech(self, text: str) -> None:
        """Convert text to speech using OpenAI's TTS and play it."""
        if not text or not self.auto_play:
            return
            
        try:
            print("🔊 Generating speech...")
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_path = temp_file.name
                
                # Generate speech using OpenAI's API
                response = self.client.audio.speech.create(
                    model="tts-1",
                    voice=self.voice,
                    input=text,
                    speed=self.speed
                )
                
                # Save to temporary file
                response.stream_to_file(temp_path)
                print("🎵 Playing audio response...")
                
                # Play the audio
                self._play_audio(temp_path)
                
                # Clean up
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    print(f"Error cleaning up temp file: {str(e)}")
            
        except Exception as e:
            print(f"🔇 Error generating speech: {str(e)}")
            
    async def play_audio(self, text: str) -> bool:
        """Play text as speech.
        
        Args:
            text: The text to convert and play
            
        Returns:
            True if playback successful, False otherwise
        """
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_path = temp_file.name
                
                # Generate speech
                response = self.client.audio.speech.create(
                    model="tts-1",
                    voice=self.voice,
                    input=text
                )
                
                # Save and play
                response.stream_to_file(temp_path)
                self._play_audio(temp_path)
                
                # Clean up
                os.unlink(temp_path)
                return True
                
        except Exception as e:
            print(f"Error playing audio: {str(e)}")
            return False 