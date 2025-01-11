"""Speech agent for text-to-speech conversion."""
import os
import tempfile
import time
from pathlib import Path
from typing import Optional
import pygame

from .base_agent import BaseAgent

SPEECH_SYSTEM_PROMPT = """You are a Speech Agent responsible for converting text to natural-sounding speech.
Focus on clear and engaging voice synthesis."""

class SpeechAgent(BaseAgent):
    """Agent for handling text-to-speech conversion."""
    
    def __init__(self):
        """Initialize the Speech Agent."""
        super().__init__(
            agent_type="speech",
            system_prompt=SPEECH_SYSTEM_PROMPT,
        )
        self.voice = "alloy"  # Default voice
        self.auto_play = True  # Default to auto-play enabled
        pygame.mixer.init()
        
    def set_voice(self, voice: str) -> str:
        """Set the TTS voice to use."""
        valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        if voice in valid_voices:
            self.voice = voice
            return f"Voice set to: {voice}"
        return f"Invalid voice. Please choose from: {', '.join(valid_voices)}"
    
    def toggle_autoplay(self) -> str:
        """Toggle auto-play setting."""
        self.auto_play = not self.auto_play
        return f"🔊 Auto-play {'enabled' if self.auto_play else 'disabled'}"
    
    def _play_audio(self, file_path: str) -> None:
        """Play audio file using pygame."""
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except Exception as e:
            print(f"Error playing audio: {str(e)}")
        
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
                    input=text
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