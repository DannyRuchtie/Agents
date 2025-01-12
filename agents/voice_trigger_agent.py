"""Voice trigger agent for wake word detection and speech recognition."""
import os
import time
import threading
import asyncio
import speech_recognition as sr
from typing import Optional, Callable
import pvporcupine
from .base_agent import BaseAgent
from .speech_agent import SpeechAgent
import pyaudio
import struct

class VoiceTriggerAgent(BaseAgent):
    """Agent that handles wake word detection and speech recognition."""
    
    def __init__(self, on_command_callback: Callable[[str], None]):
        """Initialize the voice trigger agent.
        
        Args:
            on_command_callback: Callback function to handle recognized commands
        """
        super().__init__("voice_trigger")
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.on_command = on_command_callback
        self.is_listening = False
        self.continuous_mode = False  # Whether to keep listening after processing a command
        
        # Listening timeouts (in seconds)
        self.wait_timeout = 10  # Time to wait for speech to start
        self.phrase_timeout = 15  # Maximum duration of a single command
        
        self.porcupine = None
        self.audio = None
        self.thread = None
        self.speech_agent = SpeechAgent()
        self.speech_agent.enable_speech()  # Enable speech by default for voice interactions
        
        # Check microphone permissions
        try:
            print("🎤 Checking microphone permissions...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
                print("✅ Microphone access granted!")
        except OSError as e:
            print("❌ Microphone access denied!")
            print("Please enable microphone access in System Settings:")
            print("1. Open System Settings")
            print("2. Go to Privacy & Security > Microphone")
            print("3. Enable access for Terminal or your IDE")
            print("4. Restart the application")
            raise e
    
    def set_timeouts(self, wait_timeout: int = None, phrase_timeout: int = None) -> str:
        """Set the listening timeouts.
        
        Args:
            wait_timeout: Time to wait for speech to start (in seconds)
            phrase_timeout: Maximum duration of a single command (in seconds)
        """
        if wait_timeout is not None:
            self.wait_timeout = max(5, wait_timeout)  # Minimum 5 seconds
        if phrase_timeout is not None:
            self.phrase_timeout = max(5, phrase_timeout)  # Minimum 5 seconds
        
        return f"🎤 Listening timeouts set - Wait: {self.wait_timeout}s, Phrase: {self.phrase_timeout}s"
    
    def start_listening(self):
        """Start listening for the wake word in a background thread."""
        try:
            access_key = os.getenv('PICOVOICE_ACCESS_KEY')
            if not access_key:
                raise ValueError("Picovoice access key not found in .env file")
            if access_key == "your_picovoice_access_key_here":
                raise ValueError("Please replace the placeholder with your actual Picovoice access key")
                
            # Initialize Porcupine with the default "computer" keyword
            try:
                self.porcupine = pvporcupine.create(
                    access_key=access_key,
                    keywords=['computer']
                )
            except pvporcupine.PorcupineInvalidArgumentError:
                raise ValueError("Invalid Picovoice access key. Please check your key at https://console.picovoice.ai/")
            
            self.audio = pyaudio.PyAudio()
            self.is_listening = True
            self.thread = threading.Thread(target=self._listen_loop)
            self.thread.daemon = True
            self.thread.start()
            print("🎤 Voice trigger started - listening for 'computer'...")
            
        except ValueError as e:
            print(f"\n❌ Voice Trigger Setup Error:")
            print(f"   {str(e)}")
            print("\n📝 To get a Picovoice access key:")
            print("1. Sign up at https://console.picovoice.ai/")
            print("2. Create a new access key")
            print("3. Add it to your .env file as PICOVOICE_ACCESS_KEY=your_key_here")
            self.stop_listening()
        except Exception as e:
            print(f"❌ Error starting voice trigger: {str(e)}")
            self.stop_listening()
            
    def stop_listening(self):
        """Stop listening and clean up resources."""
        self.is_listening = False
        if self.thread:
            self.thread.join(timeout=1)
        if self.porcupine:
            self.porcupine.delete()
        if self.audio:
            self.audio.terminate()
            
    def _listen_loop(self):
        """Main listening loop that runs in a background thread."""
        try:
            stream = self.audio.open(
                rate=self.porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.porcupine.frame_length
            )
            
            while self.is_listening:
                pcm = stream.read(self.porcupine.frame_length)
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                
                keyword_index = self.porcupine.process(pcm)
                if keyword_index >= 0:
                    print("\nWake word detected! Listening for command...")
                    command = self._listen_for_command()
                    if command:
                        self.on_command(command)
                        
        except Exception as e:
            print(f"Error in listening loop: {str(e)}")
        finally:
            if stream:
                stream.close()
                
    def _listen_for_command(self) -> str:
        """Listen for a command after wake word detection."""
        try:
            while True:  # Keep listening in continuous mode
                with sr.Microphone() as source:
                    print(f"🎤 Listening... (timeout in {self.wait_timeout}s)")
                    audio = self.recognizer.listen(
                        source, 
                        timeout=self.wait_timeout,
                        phrase_time_limit=self.phrase_timeout
                    )
                    print("🔍 Processing command...")
                    command = self.recognizer.recognize_google(audio)
                    print(f"✨ Recognized command: {command}")
                    
                    # Check for stop command in continuous mode
                    if self.continuous_mode and command.lower() in ["stop listening", "stop", "exit"]:
                        print("👋 Stopping continuous listening mode")
                        self.continuous_mode = False
                        return None
                    
                    # Process the command asynchronously
                    asyncio.run(self.on_command(command))
                    
                    # Break if not in continuous mode
                    if not self.continuous_mode:
                        return command
                    
                    print("\n🎤 Still listening... (say 'stop' to exit continuous mode)")
                    
        except sr.WaitTimeoutError:
            print(f"⏰ No command detected after {self.wait_timeout} seconds")
            self.speech_agent.play_sound("timeout")
        except sr.UnknownValueError:
            print("❓ Could not understand command")
            self.speech_agent.play_sound("error")
        except sr.RequestError as e:
            print(f"❌ Error with speech recognition service: {str(e)}")
        except Exception as e:
            print(f"❌ Error listening for command: {str(e)}")
        return None
    
    def process(self, text: str) -> str:
        """Process text input (not used for voice trigger agent)."""
        return "Voice trigger agent processes voice commands only." 
    
    def toggle_continuous_mode(self, enabled: bool) -> str:
        """Toggle whether to keep listening after processing a command."""
        self.continuous_mode = enabled
        return f"🎤 Continuous listening mode {'enabled' if enabled else 'disabled'}" 