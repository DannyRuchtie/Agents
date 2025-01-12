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
        """Initialize the voice trigger agent."""
        super().__init__("voice_trigger")
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.on_command = on_command_callback
        self.is_listening = False
        self.continuous_mode = False
        self.loop = None  # Store event loop reference
        
        # Listening timeouts (in seconds)
        self.wait_timeout = 10  # Time to wait for speech to start
        self.phrase_timeout = 15  # Maximum duration of a single command
        
        self.porcupine = None
        self.audio = None
        self.thread = None
        self.speech_agent = SpeechAgent()
        self.speech_agent.enable_speech()
        
        # Initialize event loop in the main thread
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
    
    async def process_command(self, command: str) -> None:
        """Process a voice command asynchronously."""
        try:
            # Get the response from the command handler
            response = await self.on_command(command)
            
            # Clean up the response by removing debug markers and system messages
            if response and isinstance(response, str):
                # Remove debug markers and system messages
                cleaned_response = self._clean_response(response)
                print(f"Speaking response: {cleaned_response}")
                # Ensure speech is enabled and speak the response
                self.speech_agent.enable_speech()  # Make sure speech is enabled
                await self.speech_agent.speak(cleaned_response)
            else:
                print("No response to speak")
        except Exception as e:
            error_msg = "I'm sorry, I encountered an error processing your request."
            print(f"Error: {str(e)}")
            await self.speech_agent.speak(error_msg)
    
    def _handle_command_sync(self, command: str) -> None:
        """Handle command in synchronous context by running it in the event loop."""
        if self.loop and command:
            future = asyncio.run_coroutine_threadsafe(
                self.process_command(command),
                self.loop
            )
            try:
                future.result(timeout=30)  # Wait for completion with timeout
            except Exception as e:
                print(f"Error executing command: {str(e)}")
    
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
            
            # Initialize PyAudio with error handling
            try:
                self.audio = pyaudio.PyAudio()
                # Test the default input device
                default_input = self.audio.get_default_input_device_info()
                print(f"Using audio input device: {default_input['name']}")
            except OSError as e:
                print("❌ Error accessing audio device. Trying alternative configuration...")
                # Clean up and try again with different settings
                if self.audio:
                    self.audio.terminate()
                self.audio = pyaudio.PyAudio()
            
            # Check microphone permissions
            try:
                print("🎤 Checking microphone permissions...")
                with sr.Microphone() as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("✅ Microphone access granted!")
            except OSError as e:
                print("❌ Microphone access denied!")
                print("Please enable microphone access in System Settings:")
                print("1. Open System Settings")
                print("2. Go to Privacy & Security > Microphone")
                print("3. Enable access for Terminal or your IDE")
                print("4. Restart the application")
                raise e
            
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
        stream = None
        try:
            # Initialize stream once at the start
            stream = self.audio.open(
                rate=self.porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.porcupine.frame_length,
                input_device_index=None
            )
            print("✅ Audio stream initialized and ready")
            
            while self.is_listening:
                try:
                    pcm = stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                    pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                    
                    keyword_index = self.porcupine.process(pcm)
                    if keyword_index >= 0:
                        print("\nWake word detected! Listening for command...")
                        self.speech_agent.play_sound("wake")
                        command = self._listen_for_command()
                        if command:
                            self._handle_command_sync(command)
                            print("\n✅ Ready for next command! Say 'computer' to start...")
                            
                except OSError as e:
                    if "Unknown Error" not in str(e):
                        print(f"⚠️ Audio stream error: {e}")
                    time.sleep(0.1)
                    continue
                    
        except Exception as e:
            print(f"❌ Error in listening loop: {str(e)}")
            
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
                print("Audio stream closed")

    def _listen_for_command(self) -> str:
        """Listen for a command after wake word detection."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                with sr.Microphone() as source:
                    print("🎤 Listening for your command...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    self.recognizer.dynamic_energy_threshold = True
                    # Increase pause threshold to detect natural speech pauses
                    self.recognizer.pause_threshold = 1.0  # Wait 1 second for pauses
                    self.recognizer.phrase_threshold = 0.3  # More sensitive to continued speech
                    self.recognizer.non_speaking_duration = 0.5  # Time needed to mark the end of speech
                    
                    print("Listening... (speak your complete command)")
                    audio = self.recognizer.listen(
                        source,
                        timeout=self.wait_timeout,
                        phrase_time_limit=None  # Remove phrase time limit to allow longer sentences
                    )
                    
                    try:
                        # Try to capture additional speech if available
                        command = self.recognizer.recognize_google(audio)
                        print("Processing initial command...")
                        
                        try:
                            # Listen for a short additional time to catch any continuation
                            print("Checking for additional speech...")
                            additional_audio = self.recognizer.listen(
                                source,
                                timeout=2.0,  # Short timeout for additional speech
                                phrase_time_limit=5.0  # Reasonable limit for continuation
                            )
                            additional_text = self.recognizer.recognize_google(additional_audio)
                            command = f"{command} {additional_text}"
                            print("Combined command parts.")
                        except (sr.WaitTimeoutError, sr.UnknownValueError):
                            # No additional speech detected, continue with original command
                            pass
                            
                        print(f"✨ Final command: {command}")
                        
                        if command.lower() in ["stop listening", "stop", "exit"]:
                            self.continuous_mode = False
                            return None
                        
                        return command
                        
                    except sr.UnknownValueError:
                        print("❓ Could not understand command. Please try again.")
                        self.speech_agent.play_sound("error")
                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"Please try again ({max_retries - retry_count} attempts remaining)")
                        continue
                        
            except sr.WaitTimeoutError:
                print("⏰ Listening timeout - say 'computer' to try again")
                self.speech_agent.play_sound("timeout")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    print(f"Retrying... ({max_retries - retry_count} attempts remaining)")
                    time.sleep(0.5)
                    continue
                break
                
        return None
    
    def process(self, text: str) -> str:
        """Process text input (not used for voice trigger agent)."""
        return "Voice trigger agent processes voice commands only." 
    
    def toggle_continuous_mode(self, enabled: bool) -> str:
        """Toggle whether to keep listening after processing a command."""
        self.continuous_mode = enabled
        return f"🎤 Continuous listening mode {'enabled' if enabled else 'disabled'}" 
    
    def _clean_response(self, response: str) -> str:
        """Clean the response by removing debug markers and system messages."""
        # Remove common debug markers
        markers_to_remove = [
            "🔍", "✨", "🎤", "❌", "✅", "⏰", "🌐",
            "Searching...",
            "Processing...",
            "I've saved this information to memory.",
            "Here's what I found:"
        ]
        
        cleaned = response
        for marker in markers_to_remove:
            cleaned = cleaned.replace(marker, "")
            
        # Remove multiple newlines and extra spaces
        cleaned = " ".join(cleaned.split())
        
        return cleaned.strip() 