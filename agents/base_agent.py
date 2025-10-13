"""Base agent module providing common functionality for all agents."""
from typing import Any, Dict, Optional, List
from datetime import datetime
import os

from config.openai_config import get_agent_config
from config.settings import debug_print, LLM_PROVIDER_SETTINGS, MODEL_SELECTOR_SETTINGS
from agents.llm_providers import get_llm_provider
from agents.model_selector import get_model_selector

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
        self._provider_cache: Dict[str, Any] = {}
        self.default_provider_name = LLM_PROVIDER_SETTINGS.get("default_provider", "openai")
        self.last_response_streamed = False
        try:
            self.llm_provider = self._get_provider(self.default_provider_name)
        except ImportError as provider_error:
            fallback_provider = "openai"
            if self.default_provider_name != fallback_provider:
                print(f"[WARN] {self.default_provider_name.title()} provider unavailable ({provider_error}). Falling back to OpenAI.")
                self.default_provider_name = fallback_provider
                LLM_PROVIDER_SETTINGS["default_provider"] = fallback_provider
                MODEL_SELECTOR_SETTINGS["use_ollama_for_simple"] = False
            self.llm_provider = self._get_provider(fallback_provider)
        self.model_selector = get_model_selector()  # Initialize model selector
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

    def _get_provider(self, provider_name: str):
        """Return a cached provider instance for the requested name."""
        normalized_name = provider_name.lower()
        if normalized_name not in self._provider_cache:
            self._provider_cache[normalized_name] = get_llm_provider(normalized_name)
        return self._provider_cache[normalized_name]
    
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

    async def _invoke_provider(
        self,
        provider,
        messages: List[Dict[str, Any]],
        config: Dict[str, Any],
        provider_name: str
    ) -> tuple[str, str]:
        """Invoke an LLM provider and return its response text along with the provider used."""
        assistant_response_parts: List[str] = []
        stream = provider.stream_chat_completion(messages=messages, config=config)
        async for content_chunk in stream:
            if content_chunk is not None:
                assistant_response_parts.append(content_chunk)
        assistant_message = "".join(assistant_response_parts)
        self.last_response_streamed = False  # Responses are surfaced later by the caller
        return assistant_message, provider_name

    def _should_retry_with_openai(self, response: str, provider_name: str) -> bool:
        """Heuristic to decide if a local response should be retried with OpenAI."""
        if provider_name != "ollama" or self.agent_type != "master":
            return False

        lower = response.lower().strip()
        fallback_triggers = [
            "i am a large language model",
            "as a large language model",
            "i'm a large language model",
            "i am an ai language model",
            "i'm an ai language model",
            "i do not have access to personal",
            "i don't have access to personal",
            "i don't have personal knowledge",
            "i do not have personal knowledge",
            "i'm ready to be your ai assistant",
            "i am ready to be your ai assistant"
        ]
        return any(trigger in lower for trigger in fallback_triggers)
    
    async def process(self, input_text: str, messages: Optional[List[Dict[str, str]]] = None, system_prompt_override: Optional[str] = None, **kwargs: Any) -> str:
        """Process the input text and return a response."""
        self.last_response_streamed = False
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
                return response_text
            
            # Use provided messages or build from context window
            current_messages: List[Dict[str, str]]
            
            # Determine the system prompt to use
            active_system_prompt = system_prompt_override if system_prompt_override is not None else self.system_prompt

            if messages:
                # For vision messages, use them directly without modification
                if any(isinstance(msg.get('content'), list) and 
                      any(item.get('type') == 'image_url' for item in msg['content']) 
                      for msg in messages):
                    current_messages = messages # Vision messages might already include a system-like prompt or structure
                else:
                    # Prepend the active system prompt to the provided messages
                    # Ensure not to add duplicate system messages if 'messages' already has one.
                    if not (messages and messages[0]["role"] == "system"):
                        current_messages = [{"role": "system", "content": active_system_prompt}] + messages
                    else:
                        # If messages[0] is already a system prompt, decide whether to replace or use it.
                        # For now, let's assume if messages has a system prompt, it's intentional.
                        # However, system_prompt_override should take precedence.
                        if system_prompt_override is not None:
                            messages[0]["content"] = system_prompt_override # Override existing system message
                        current_messages = messages 

            else:
                current_messages = [{"role": "system", "content": active_system_prompt}]
                current_messages.extend(self.conversation_history)
                current_messages.append({"role": "user", "content": input_text})
            
            # Use ModelSelector to intelligently choose the model (unless overridden)
            selected_model_info = None
            if "model" not in kwargs and MODEL_SELECTOR_SETTINGS.get("enabled", True):
                # Auto-select model based on task complexity
                selected_model_info = self.model_selector.get_model_for_agent(
                    agent_type=self.agent_type,
                    prompt=input_text
                )
                debug_print(f"ModelSelector chose: {selected_model_info['model']} (complexity: {selected_model_info['complexity']})")

            # Extract model configuration
            config = {
                "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
                "seed": kwargs.get("seed", self.config.get("seed")),
                "response_format": kwargs.get("response_format", self.config.get("response_format")) # Let provider handle default if None
            }
            # Allow callers to explicitly limit completions without enforcing defaults
            if "max_completion_tokens" in kwargs:
                config["max_completion_tokens"] = kwargs["max_completion_tokens"]
            elif "max_tokens" in kwargs:
                config["max_completion_tokens"] = kwargs["max_tokens"]
            elif "max_completion_tokens" in self.config:
                config["max_completion_tokens"] = self.config["max_completion_tokens"]
            
            # Add model - priority: kwargs > model_selector > provider default
            if "model" in kwargs:
                config["model"] = kwargs["model"]
            elif selected_model_info:
                config["model"] = selected_model_info["model"]
            
            # Filter out None values from config to avoid sending them if not set
            config = {k: v for k, v in config.items() if v is not None}

            model_name = config.get("model", "")
            if model_name and model_name.lower().startswith("o"):
                # Reasoning models like o1 only allow default temperature/penalties
                config.pop("temperature", None)
                config.pop("response_format", None)  # Let API decide defaults for reasoning models
            
            # Determine provider for this request
            provider_name = self.default_provider_name
            if selected_model_info and selected_model_info.get("provider"):
                provider_name = selected_model_info["provider"].lower()

            try:
                provider = self._get_provider(provider_name)
            except Exception as provider_error:
                debug_print(f"Falling back to default provider due to error with '{provider_name}': {provider_error}")
                provider_name = self.default_provider_name
                provider = self._get_provider(provider_name)
                # If we fell back from a non-default provider, ensure model name matches provider
                if selected_model_info and selected_model_info.get("provider") != provider_name:
                    if provider_name == "openai":
                        config["model"] = MODEL_SELECTOR_SETTINGS.get("simple_model", config.get("model"))

            # Update cached provider reference for compatibility
            self.llm_provider = provider

            assistant_message, provider_name = await self._invoke_provider(
                provider=provider,
                messages=current_messages,
                config=config,
                provider_name=provider_name
            )

            if self._should_retry_with_openai(assistant_message, provider_name):
                debug_print("BaseAgent: Local model response flagged as low quality. Retrying with OpenAI.")
                fallback_provider = self._get_provider("openai")
                fallback_config = config.copy()
                # Ensure model aligns with OpenAI simple default
                fallback_config["model"] = MODEL_SELECTOR_SETTINGS.get("simple_model", LLM_PROVIDER_SETTINGS.get("openai_default_model"))
                assistant_message, provider_name = await self._invoke_provider(
                    provider=fallback_provider,
                    messages=current_messages,
                    config=fallback_config,
                    provider_name="openai"
                )
                self.llm_provider = fallback_provider
            
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
            self.last_response_streamed = False
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
