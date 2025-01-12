"""Speech agent for text-to-speech conversion."""
import os
import tempfile
import time
from pathlib import Path
from typing import Optional
import pygame

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
        self.speech_dir = get_path('speech_output')
        self.voice = "nova"  # Default to a more energetic voice
        self.speed = 1.0  # Default speed (1.0 = normal, >1 = faster, <1 = slower)
        self.auto_play = True  # Default to auto-play enabled
        pygame.mixer.init()
    
    def enable_speech(self) -> str:
        """Enable speech output."""
        self.auto_play = True
        return "🔊 Speech output enabled"
    
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
        try:
            pygame.mixer.music.load(file_path)
            # Adjust playback speed if different from normal
            if self.speed != 1.0:
                pygame.mixer.music.set_pos(0)  # Reset position
                pygame.mixer.music.play(loops=0, start=0.0, fade_ms=0)
                pygame.mixer.music.set_pos(0)  # Apply speed change
                pygame.time.Clock().tick(44100 * self.speed)  # Adjust playback speed
            else:
                pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except Exception as e:
            print(f"Error playing audio: {str(e)}")
    
    def play_sound(self, sound_type: str) -> None:
        """Play a system sound."""
        # TODO: Implement system sounds for different events
        pass
        
    async def speak(self, text: str) -> None:
        """Speak the given text using text-to-speech.
        
        Args:
            text: The text to speak
        """
        await self.text_to_speech(text)
        
    async def text_to_speech(self, text: str) -> None:
        """Convert text to speech using OpenAI's TTS and play it.
        
        Args:
            text: The text to convert to speech
        """
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_path = temp_file.name
                
                # Generate speech using OpenAI's API
                response = self.client.audio.speech.create(
                    model="tts-1",
                    voice=self.voice,
                    input=text,
                    speed=self.speed  # Apply speed adjustment
                )
                
                # Save to temporary file
                response.stream_to_file(temp_path)
                
                # Auto-play if enabled
                if self.auto_play:
                    self._play_audio(temp_path)
                
                # Clean up the temporary file
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    print(f"Error cleaning up temporary file: {str(e)}")
            
        except Exception as e:
            print(f"Error generating speech: {str(e)}")
            
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