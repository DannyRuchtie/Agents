import asyncio
import sys
from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator

# from config.openai_config import get_client as get_openai_client # Removed
from config.openai_config import get_async_openai_client
from config.settings import LLM_PROVIDER_SETTINGS, debug_print

# Attempt to import ollama, but don't fail if not installed yet
try:
    import ollama
except ImportError:
    ollama = None # Will be checked before trying to use OllamaProvider
    debug_print("Ollama library not found. OllamaProvider will not be available unless installed.")

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    @abstractmethod
    async def stream_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion from the LLM.

        Args:
            messages: A list of message dictionaries (e.g., {'role': 'user', 'content': ...}).
            config: A dictionary with model-specific configurations (e.g., model name, temperature).

        Yields:
            str: Chunks of the assistant's response.
        """
        # This is an abstract method, so it needs to yield properly for type hinting if anyone calls super().
        # However, concrete implementations should not call super() for this method.
        if False: # pragma: no cover
            yield ""

class OpenAILLMProvider(BaseLLMProvider):
    """LLM Provider for OpenAI models."""
    def __init__(self):
        self.client = get_async_openai_client()
        if not self.client:
            raise ValueError("Async OpenAI client could not be initialized. Check API key.")

    async def stream_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        # Ensure 'model' is in config, defaulting if necessary
        model_name = config.get("model", LLM_PROVIDER_SETTINGS.get("openai_default_model", "gpt-4.1-nano-2025-04-14"))
        
        openai_config = {
            "model": model_name,
            "temperature": config.get("temperature", 0.7),
            "max_tokens": config.get("max_tokens", 4096),
            "presence_penalty": config.get("presence_penalty", 0.6),
            "frequency_penalty": config.get("frequency_penalty", 0.5),
            "seed": config.get("seed"),
            "response_format": config.get("response_format", {"type": "text"})
        }
        # Filter out None values from config, as OpenAI API doesn't like None for some params
        openai_config = {k: v for k, v in openai_config.items() if v is not None}


        debug_print(f"OpenAILLMProvider: Streaming chat completion with config: {openai_config} and messages: {messages}")
        stream = await self.client.chat.completions.create(
            messages=messages,
            stream=True,
            **openai_config
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content is not None:
                yield content

class OllamaLLMProvider(BaseLLMProvider):
    """LLM Provider for Ollama models."""
    def __init__(self):
        if ollama is None:
            raise ImportError("Ollama library is not installed. Please install it with 'pip install ollama'.")
        
        # AsyncClient can be instantiated per call or once, depending on preference and httpx behavior.
        # For now, let's create it here. It uses httpx.AsyncClient internally.
        self.client = ollama.AsyncClient(host=LLM_PROVIDER_SETTINGS.get("ollama_base_url"))
        debug_print(f"OllamaLLMProvider initialized with base URL: {LLM_PROVIDER_SETTINGS.get('ollama_base_url')}")

    async def stream_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        model_name = config.get("model", LLM_PROVIDER_SETTINGS.get("ollama_default_model"))
        
        # Ollama's API takes options within a separate 'options' dictionary
        ollama_options = {
            key: config[key] for key in ["temperature", "seed", "num_predict", "top_k", "top_p"] if key in config
            # 'max_tokens' for OpenAI is 'num_predict' for Ollama. Add more mappings as needed.
        }
        if "max_tokens" in config: # Mapping max_tokens to num_predict
             ollama_options["num_predict"] = config["max_tokens"]


        # Prepare messages for Ollama: it expects 'role' and 'content'.
        # Also, ensure image_url content is handled correctly if we extend this for vision with Ollama.
        # For now, assuming text messages.
        ollama_messages = []
        for msg in messages:
            if msg.get("role") == "system" and not msg.get("content"): # Skip empty system prompts
                continue
            
            # Ollama expects string content. If content is a list (e.g. for OpenAI vision),
            # we need to adapt it. For now, assuming simple text content based on BaseAgent.
            # If BaseAgent sends complex content, this part needs more robust handling.
            content = msg.get("content")
            if isinstance(content, list):
                # Attempt to extract text part for Ollama, or join text parts.
                # This is a simplification. For multi-modal with Ollama, more sophisticated handling is needed.
                text_parts = [item.get("text") for item in content if isinstance(item, dict) and item.get("type") == "text"]
                processed_content = " ".join(filter(None, text_parts))
                if not processed_content: # Fallback if no text parts found, maybe take first item if string?
                    debug_print(f"Warning: Complex message content for Ollama, could not extract simple text: {content}")
                    processed_content = str(content) # Fallback, might not be ideal
            else:
                processed_content = content

            ollama_messages.append({"role": msg.get("role"), "content": processed_content})


        debug_print(f"OllamaLLMProvider: Streaming chat completion for model '{model_name}' with options: {ollama_options} and messages: {ollama_messages}")
        
        stream_kwargs = {"model": model_name, "messages": ollama_messages}
        if ollama_options:
            stream_kwargs["options"] = ollama_options
            
        try:
            async for part in await self.client.chat(**stream_kwargs, stream=True):
                content = part.get("message", {}).get("content")
                if content:
                    yield content
        except Exception as e:
            # Log the error and yield an error message or re-raise
            error_msg = f"Ollama API error: {str(e)}"
            debug_print(error_msg)
            yield error_msg # Or handle more gracefully


def get_llm_provider() -> BaseLLMProvider:
    """Factory function to get the configured LLM provider."""
    provider_name = LLM_PROVIDER_SETTINGS.get("default_provider", "ollama")
    debug_print(f"Getting LLM provider: {provider_name}")
    if provider_name == "openai":
        return OpenAILLMProvider()
    elif provider_name == "ollama":
        if ollama is None:
            raise ImportError("Ollama library is not installed. Please install it with 'pip install ollama' to use the Ollama provider.")
        return OllamaLLMProvider()
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_name}") 