from typing import Optional
import re
import tempfile
import os

class MasterAgent(BaseAgent):
    """Master agent that coordinates all other agents."""
    
    def __init__(self):
        # Define personality traits and settings
        self.personality = {
            "humor_level": 0.5,  # 0.0 to 1.0: serious to very humorous
            "formality_level": 0.5,  # 0.0 to 1.0: casual to very formal
            "emoji_usage": True,  # Whether to use emojis in responses
            "traits": {
                "witty": True,
                "empathetic": True,
                "curious": True,
                "enthusiastic": True
            }
        }
        
        # Update system prompt with personality
        personality_prompt = self._generate_personality_prompt()
        system_prompt = f"{MASTER_SYSTEM_PROMPT}\n\n{personality_prompt}"
        
        super().__init__(
            agent_type="master",
            system_prompt=system_prompt,
        )
        
        # Initialize speech agent first since voice trigger needs it
        self.speech_agent = SpeechAgent()
        
        # Initialize other sub-agents
        self.memory_agent = MemoryAgent()
        self.search_agent = SearchAgent()
        self.writer_agent = WriterAgent()
        self.code_agent = CodeAgent()
        self.scanner_agent = ScannerAgent()
        self.vision_agent = VisionAgent()
        self.location_agent = LocationAgent()
        self.learning_agent = LearningAgent()
        
        # Initialize voice trigger agent with speech agent
        self.voice_trigger = VoiceTriggerAgent(self.handle_voice_command, self.speech_agent)
        
        # Environment and state flags
        self.speech_mode = False
        self.os_type = "macos"  # Running on macOS
        self.has_location_access = True
        self.has_screen_access = True
        self.conversation_depth = 0  # Track conversation depth for a topic
        
        # Ensure required directories exist
        ensure_directories()
        
    async def process(self, query: str, image_path: Optional[str] = None) -> str:
        """Process a user query and coordinate agent responses."""
        query_lower = query.lower().strip()
        
        print("\n=== Processing Query ===")
        print(f"Query: {query}")
        print(f"Speech enabled: {self.speech_agent.is_speech_enabled()}")
        print(f"Auto-play: {self.speech_agent.auto_play}")
        
        # Handle speech-related commands first
        if query_lower in ["enable speech", "turn on speech", "speech on", "enable speach", "speach on", "speach enable"]:
            print("\n=== Enabling Speech Debug ===")
            try:
                print("1. Current speech agent status:")
                print(f"   - is_speech_enabled(): {self.speech_agent.is_speech_enabled()}")
                print(f"   - auto_play: {self.speech_agent.auto_play}")
                
                # Enable speech
                print("\n2. Calling enable_speech()...")
                result = self.speech_agent.enable_speech()
                print(f"3. Enable speech result: {result}")
                
                print("\n4. Updated speech agent status:")
                print(f"   - is_speech_enabled(): {self.speech_agent.is_speech_enabled()}")
                print(f"   - auto_play: {self.speech_agent.auto_play}")
                
                if "Failed" in result:
                    return result
                
                # Prepare and speak confirmation
                confirmation = "Speech has been enabled. I will now speak my responses."
                print(f"\n5. Speaking confirmation: {confirmation}")
                
                # Start speaking confirmation asynchronously
                print("6. Calling speech_agent.speak()...")
                try:
                    await self.speech_agent.speak(confirmation)
                    print("7. speak() method completed")
                except Exception as e:
                    print(f"❌ Error in speak(): {str(e)}")
                    raise
                
                return "Speech enabled and TTS started"
                
            except Exception as e:
                print(f"❌ Error enabling speech: {str(e)}")
                return f"Failed to enable speech: {str(e)}"
            
        if query_lower in ["disable speech", "turn off speech", "speech off"]:
            return self.speech_agent.disable_speech()
            
        if query_lower == "test speech":
            print("\n=== Testing Speech ===")
            try:
                if not self.speech_agent.is_speech_enabled():
                    print("Speech is disabled, enabling...")
                    result = self.speech_agent.enable_speech()
                    print(f"Enable result: {result}")
                    if "Failed" in result:
                        return result
                
                test_message = "This is a test of the text to speech system."
                print(f"\nTesting TTS with message: {test_message}")
                print(f"Speech enabled: {self.speech_agent.is_speech_enabled()}")
                print(f"Voice: {self.speech_agent.voice}")
                print(f"Speed: {self.speech_agent.speed}")
                print(f"Output directory: {self.speech_agent.speech_dir}")
                
                print("\nCalling speech_agent.speak()...")
                try:
                    await self.speech_agent.speak(test_message)
                    print("Speech completed successfully")
                    return "Speech test completed successfully. Check the speech_output directory for the generated audio files."
                except Exception as e:
                    print(f"❌ Error in speak(): {str(e)}")
                    raise
            except Exception as e:
                print(f"❌ Speech test failed: {str(e)}")
                return f"Speech test failed: {str(e)}"
            
        if query_lower.startswith("set voice "):
            voice = query_lower.replace("set voice ", "").strip()
            response = self.speech_agent.set_voice(voice)
            if self.speech_agent.is_speech_enabled():
                await self.speech_agent.speak(f"Voice set to {voice}")
            return response
            
        if query_lower.startswith("set speed "):
            try:
                speed = float(query_lower.replace("set speed ", "").strip())
                response = self.speech_agent.set_speed(speed)
                if self.speech_agent.is_speech_enabled():
                    await self.speech_agent.speak(f"Speed set to {speed}")
                return response
            except ValueError:
                return "Please provide a valid speed between 0.5 and 2.0"
        
        # Process normal queries
        try:
            # Get response from base agent
            response = await super().process(query)
            print(f"\nGot response: {response}")
            
            # Start speaking the response asynchronously if speech is enabled
            if self.speech_agent.is_speech_enabled():
                print("\n=== Speaking Response Debug ===")
                print(f"1. Speech agent status:")
                print(f"   - is_speech_enabled(): {self.speech_agent.is_speech_enabled()}")
                print(f"   - auto_play: {self.speech_agent.auto_play}")
                print(f"   - voice: {self.speech_agent.voice}")
                print(f"   - speed: {self.speech_agent.speed}")
                
                cleaned_response = self._clean_response_for_speech(response)
                print(f"2. Cleaned response: {cleaned_response}")
                
                print("3. Calling speech_agent.speak()...")
                try:
                    await self.speech_agent.speak(cleaned_response)
                    print("4. speak() method completed")
                except Exception as e:
                    print(f"❌ Error in speak(): {str(e)}")
                    raise
            else:
                print("\nSpeech is disabled. Enable it with 'enable speech'")
            
            return response
            
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def _clean_response_for_speech(self, response: str) -> str:
        """Clean a response to make it more suitable for speech output."""
        # Remove common formatting and debug markers
        markers = ["🔍", "📚", "🌐", "💻", "📸", "📄", "🖼️", "📍", "🤖", "✨", "•"]
        cleaned = response
        
        for marker in markers:
            cleaned = cleaned.replace(marker, "")
            
        # Remove URLs and technical formatting
        cleaned = re.sub(r'http[s]?://\S+', '', cleaned)
        cleaned = re.sub(r'```[^`]*```', '', cleaned)
        
        # Remove multiple newlines and spaces
        cleaned = " ".join(cleaned.split())
        
        return cleaned.strip() 

    async def handle_voice_command(self, command: str):
        """Handle voice commands by processing them and speaking the response."""
        try:
            print("\n=== Voice Command Debug ===")
            print(f"1. Received command: {command}")
            
            # Process the command
            print("2. Processing command...")
            response = await self.process(command)
            
            # Clean the response for speech
            cleaned_response = self._clean_response_for_speech(response)
            print(f"3. Cleaned response: {cleaned_response}")
            
            # Ensure speech is enabled and speak the response
            if not self.speech_agent.is_speech_enabled():
                print("4. Enabling speech for voice response...")
                self.speech_agent.enable_speech()
            
            print("5. Speaking response...")
            await self.speech_agent.speak(cleaned_response)
            print("=== Voice Command End ===\n")
            
            return response
            
        except Exception as e:
            error_msg = f"Error processing voice command: {str(e)}"
            print(f"❌ {error_msg}")
            if self.speech_agent.is_speech_enabled():
                await self.speech_agent.speak("Sorry, I encountered an error processing your voice command.")
            return error_msg 