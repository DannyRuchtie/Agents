"""Base agent module providing common functionality for all agents."""
from typing import Any, Dict, Optional, List
from datetime import datetime

from config.openai_config import get_client, get_agent_config


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
        
        # Set more conversational parameters
        if "temperature" not in self.config:
            self.config["temperature"] = 0.8  # More creative and conversational
        if "presence_penalty" not in self.config:
            self.config["presence_penalty"] = 0.6  # Encourage more varied responses
        if "frequency_penalty" not in self.config:
            self.config["frequency_penalty"] = 0.5  # Discourage repetitive responses
    
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
    
    async def process(self, input_text: str, **kwargs: Any) -> str:
        """Process the input text and return a response."""
        try:
            # Handle common greetings more naturally
            greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
            if input_text.lower().strip() in greetings:
                return "Hey! Great to see you! How can I help you today? 😊"
            
            # Get current context window with system prompt and history
            messages = self.get_context_window()
            messages.append({"role": "user", "content": input_text})
            
            # Extract model configuration
            config = {
                "model": self.config["model"],
                "temperature": self.config.get("temperature", 0.7),
                "max_tokens": self.config.get("max_tokens", 4096),
                "seed": self.config.get("seed"),
                "response_format": self.config.get("response_format", {"type": "text"})
            }
            config.update(kwargs)
            
            # Make the API call without await
            completion = self.client.chat.completions.create(
                messages=messages,
                **config
            )
            
            # Extract assistant's response
            assistant_message = completion.choices[0].message.content
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": input_text})
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            # Trim history if needed
            self._trim_history()
            
            return assistant_message
            
        except Exception as e:
            print(f"Error in OpenAI API call: {str(e)}")
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