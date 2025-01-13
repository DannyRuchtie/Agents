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
        
        # Initialize sub-agents
        self.memory_agent = MemoryAgent()
        self.search_agent = SearchAgent()
        self.writer_agent = WriterAgent()
        self.code_agent = CodeAgent()
        self.scanner_agent = ScannerAgent()
        self.vision_agent = VisionAgent()
        self.location_agent = LocationAgent()
        self.learning_agent = LearningAgent()
        
        # Environment and state flags
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
        
        # Process normal queries
        try:
            # Get response from base agent
            response = await super().process(query)
            print(f"\nGot response: {response}")
            return response
            
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg 