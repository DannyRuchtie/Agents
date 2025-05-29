"""Base agent module providing common functionality for all agents."""
from typing import Any, Dict, Optional, List
from datetime import datetime
import os
import sys # Added for streaming

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
            # Check if this is an image request and we're not already the vision agent
            if self.agent_type != "vision" and self._is_image_path(input_text):
                from agents.vision_agent import VisionAgent
                vision_agent = VisionAgent()
                image_path, query = self._extract_image_path(input_text)
                # Vision agent responses are not typically streamed in the same way as text,
                # but if its analyze_image calls this process method, it would stream.
                # For now, assume vision_agent.analyze_image handles its own output.
                return await vision_agent.analyze_image(image_path, query)
            
            # Handle common greetings more naturally
            if not messages and input_text.lower().strip() in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]:
                response_text = "Hey! Great to see you! How can I help you today? 😊"
                print(response_text) # Print directly for simple non-LLM responses
                return response_text
            
            # Use provided messages or build from context window
            current_messages: List[Dict[str, str]]
            if messages:
                # For vision messages, use them directly without modification
                if any(isinstance(msg.get('content'), list) and 
                      any(item.get('type') == 'image_url' for item in msg['content']) 
                      for msg in messages):
                    current_messages = messages
                else:
                    current_messages = [{"role": "system", "content": self.system_prompt}, *messages]
            else:
                current_messages = self.get_context_window()
                current_messages.append({"role": "user", "content": input_text})
            
            # Extract model configuration
            config = {
                "model": kwargs.get("model", self.config["model"]),  # Allow model override
                "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
                "max_tokens": kwargs.get("max_tokens", self.config.get("max_tokens", 4096)),
                "seed": kwargs.get("seed", self.config.get("seed")),\
                "response_format": kwargs.get("response_format", self.config.get("response_format", {"type": "text"}))
            }
            
            # Make the API call with streaming
            stream = self.client.chat.completions.create(
                messages=current_messages,
                stream=True, # Enable streaming
                **config
            )
            
            assistant_response_parts = []
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content is not None:
                    sys.stdout.write(content)
                    sys.stdout.flush()
                    assistant_response_parts.append(content)
            
            sys.stdout.write("\\n") # Add a newline after the streamed response is complete
            sys.stdout.flush()

            assistant_message = "".join(assistant_response_parts)
            
            # Only update conversation history if using standard input_text and not pre-defined messages
            # This logic might need refinement: if `messages` were passed (e.g. for routing), 
            # we might not want to add the user's `input_text` to history here.
            # The original history update was guarded by `if not messages:`. Let's keep that for now.
            # However, the `input_text` is the *user's* direct query in the main loop.
            # The `messages` argument is more for internal calls like the routing decision.
            # The key is that an agent's response should be added to *its own* history if applicable.
            # MasterAgent has its own history. Other agents have their own.
            # This BaseAgent's history is for when it's used directly or as a fallback.

            # If this `process` call was initiated by a user query (i.e., `messages` was None initially),
            # then input_text and assistant_message form a pair for this agent's history.
            if messages is None or not any(m['role'] == 'user' and m['content'] == input_text for m in messages):
                 # This condition ensures we only add to history if `input_text` was the primary query
                 # and not part of an internal `messages` list.
                 # A bit complex, if messages were passed, they already contain the history.
                 # The original check was `if not messages:`. This is safer.
                 # Let's simplify back to the original check for clarity:
                 # if `messages` were provided, they constitute the full context for this call.
                 # if `messages` were NOT provided, then `input_text` is the new user turn.
                if not messages: # Reverted to original logic for history update.
                    self.conversation_history.append({"role": "user", "content": input_text})
                    self.conversation_history.append({"role": "assistant", "content": assistant_message})
                    self._trim_history()

            return assistant_message
            
        except Exception as e:
            error_message = f"I encountered an error: {str(e)}"
            print(error_message) # Print error as well
            return error_message
    
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