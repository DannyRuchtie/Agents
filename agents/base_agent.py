"""Base agent module providing common functionality for all agents."""
from typing import Any, Dict, Optional, List
from datetime import datetime
import os

from config.openai_config import get_client, get_agent_config
from config.settings import debug_print

# Image file extensions that should be routed to vision agent
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

class BaseAgent:
    """Base agent class with common functionality."""
    
    def __init__(
        self,
        agent_type: str,
        system_prompt: str = """I'm your friendly AI assistant who helps you with anything you need. I talk naturally and casually, like a helpful friend would.

When you ask me something, I:
- Keep my responses friendly and personal
- Stay practical and helpful
- Use a casual, conversational tone
- Avoid academic or encyclopedic responses
- Focus on being genuinely helpful

I should sound like a friend who's knowledgeable but approachable, always ready to help with whatever you need.""",
        max_history: int = 10
    ):
        """Initialize the base agent."""
        self.client = get_client()
        self.config = get_agent_config(agent_type)
        self.system_prompt = system_prompt
        self.max_history = max_history
        self.conversation_history: List[Dict[str, str]] = []
        self.conversation_start = datetime.now()
        self.agent_type = agent_type
        
        # Set more conversational parameters
        if "temperature" not in self.config:
            self.config["temperature"] = 0.8  # More creative and conversational
        if "presence_penalty" not in self.config:
            self.config["presence_penalty"] = 0.6  # Encourage more varied responses
        if "frequency_penalty" not in self.config:
            self.config["frequency_penalty"] = 0.5  # Discourage repetitive responses
    
    def _is_image_path(self, text: str) -> bool:
        """Check if the text contains a valid image file path."""
        # Extract potential file paths from text
        words = text.split()
        for word in words:
            # Remove quotes if present
            word = word.strip("'\"")
            if os.path.exists(word):
                ext = os.path.splitext(word)[1].lower()
                if ext in IMAGE_EXTENSIONS:
                    return True
        return False

    def _extract_image_path(self, text: str) -> tuple[str, str]:
        """Extract image path and remaining query from text."""
        words = text.split()
        for i, word in enumerate(words):
            # Remove quotes if present
            word = word.strip("'\"")
            if os.path.exists(word):
                ext = os.path.splitext(word)[1].lower()
                if ext in IMAGE_EXTENSIONS:
                    # Return the path and the rest of the query
                    remaining_words = words[:i] + words[i+1:]
                    return word, ' '.join(remaining_words)
        return '', text

    def _trim_history(self) -> None:
        """Trim conversation history to max_history message pairs."""
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-(self.max_history * 2):]
    
    def get_context_window(self) -> List[Dict[str, str]]:
        """Get the current context window for the conversation."""
        return [
            {"role": "system", "content": self.system_prompt},
            *self.conversation_history
        ]
    
    async def process(self, input_text: str, messages: Optional[List[Dict[str, str]]] = None, **kwargs: Any) -> str:
        """Process the input text and return a response."""
        try:
            print("\n=== Base Agent Processing ===")
            print(f"Input text: {input_text}")
            print(f"Messages: {messages}")
            print(f"Agent type: {self.agent_type}")
            
            # Check if this is an image request and we're not already the vision agent
            if self.agent_type != "vision" and self._is_image_path(input_text):
                print("Detected image path, routing to vision agent...")
                from agents.vision_agent import VisionAgent
                vision_agent = VisionAgent()
                image_path, query = self._extract_image_path(input_text)
                return await vision_agent.analyze_image(image_path, query)
            
            # Handle common greetings more naturally
            if not messages and input_text.lower().strip() in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]:
                return "Hey! Great to see you! How can I help you today? 😊"
            
            # Use provided messages or build from context window
            if messages:
                print("Using provided messages")
                # For vision messages, use them directly without modification
                if any(isinstance(msg.get('content'), list) and 
                      any(item.get('type') == 'image_url' for item in msg['content']) 
                      for msg in messages):
                    print("Detected vision message format")
                else:
                    messages = [{"role": "system", "content": self.system_prompt}, *messages]
            else:
                print("Building messages from context window")
                messages = self.get_context_window()
                messages.append({"role": "user", "content": input_text})
            
            # Extract model configuration
            config = {
                "model": kwargs.get("model", self.config["model"]),  # Allow model override
                "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
                "max_tokens": kwargs.get("max_tokens", self.config.get("max_tokens", 4096)),
                "seed": kwargs.get("seed", self.config.get("seed")),
                "response_format": kwargs.get("response_format", self.config.get("response_format", {"type": "text"}))
            }
            
            print("\nFinal Configuration:")
            print(f"Model: {config['model']}")
            print(f"Temperature: {config['temperature']}")
            print(f"Max tokens: {config['max_tokens']}")
            print("\nFinal Messages:")
            for msg in messages:
                print(f"Role: {msg['role']}")
                if isinstance(msg['content'], list):
                    print("Content (list):")
                    for item in msg['content']:
                        print(f"  - Type: {item.get('type')}")
                        if item.get('type') == 'image_url':
                            print(f"  - Image URL present")
                        else:
                            print(f"  - Content: {item.get('text', '')}")
                else:
                    print(f"Content: {msg['content']}")
            
            # Make the API call
            print("\nMaking API call...")
            completion = self.client.chat.completions.create(
                messages=messages,
                **config
            )
            
            # Extract assistant's response
            assistant_message = completion.choices[0].message.content
            print(f"\nAPI Response: {assistant_message[:100]}...")
            
            # Only update conversation history if using standard input
            if not messages:
                self.conversation_history.append({"role": "user", "content": input_text})
                self.conversation_history.append({"role": "assistant", "content": assistant_message})
                self._trim_history()
            
            return assistant_message
            
        except Exception as e:
            error_msg = f"Error in OpenAI API call: {str(e)}"
            print(f"\nERROR: {error_msg}")
            return f"I encountered an error: {str(e)}"
    
    def clear_history(self) -> None:
        """Clear the conversation history and reset start time."""
        self.conversation_history = []
        self.conversation_start = datetime.now()
    
    def get_conversation_info(self) -> Dict[str, Any]:
        """Get information about the current conversation."""
        return {
            "message_count": len(self.conversation_history) // 2,
            "start_time": self.conversation_start.isoformat(),
            "history_limit": self.max_history,
            "current_length": len(self.conversation_history)
        } 