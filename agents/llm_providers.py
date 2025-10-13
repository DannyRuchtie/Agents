import asyncio
import sys
from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator
import json
import httpx

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
        
        max_completion_tokens = config.get("max_completion_tokens")
        if max_completion_tokens is None and "max_tokens" in config:
            max_completion_tokens = config["max_tokens"]

        openai_config = {
            "model": model_name,
            "temperature": config.get("temperature"),
            "presence_penalty": config.get("presence_penalty"),
            "frequency_penalty": config.get("frequency_penalty"),
            "seed": config.get("seed"),
            "response_format": config.get("response_format")
        }
        if max_completion_tokens is not None:
            openai_config["max_completion_tokens"] = max_completion_tokens
        # Filter out None values from config, as OpenAI API doesn't like None for some params
        openai_config = {k: v for k, v in openai_config.items() if v is not None}
        # Remove legacy max_tokens key if present
        config.pop("max_tokens", None)


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
        """Stream chat completion from Ollama, supporting multimodal if image data is present."""
        model_name = config.get("model") or LLM_PROVIDER_SETTINGS.get("ollama_default_model")
        
        processed_messages = []
        image_data_b64_list = [] # To store base64 image strings for Ollama

        # Check messages for image content (as structured by VisionAgent for OpenAI)
        # and reformat for Ollama
        is_vision_request = False
        for msg in messages:
            if msg["role"] == "user" and isinstance(msg["content"], list):
                text_content_parts = []
                for content_item in msg["content"]:
                    if content_item["type"] == "text":
                        text_content_parts.append(content_item["text"])
                    elif content_item["type"] == "image_url":
                        image_url_data = content_item["image_url"]["url"]
                        # Expected format: "data:[<mediatype>];base64,<data>"
                        if image_url_data.startswith("data:image/") and ";base64," in image_url_data:
                            base64_image_data = image_url_data.split(";base64,", 1)[1]
                            image_data_b64_list.append(base64_image_data)
                            is_vision_request = True
                
                # Consolidate text parts for this message
                full_text_content = "\n".join(text_content_parts)
                if full_text_content or image_data_b64_list: # Add message if there's text or image
                    processed_messages.append({"role": msg["role"], "content": full_text_content})

            elif isinstance(msg["content"], str): # Standard text message
                processed_messages.append({"role": msg["role"], "content": msg["content"]})
            else:
                # Fallback for unexpected message structure, treat as text if possible
                try:
                    processed_messages.append({"role": msg["role"], "content": str(msg["content"])})
                except Exception:
                    debug_print(f"OllamaProvider: Could not process complex message content: {msg['content']}")
                    processed_messages.append({"role": msg["role"], "content": "[Unsupported content format]"})


        if is_vision_request:
            # Override model_name if it's a vision request and a specific vision model is set
            vision_model_override = LLM_PROVIDER_SETTINGS.get("ollama_default_vision_model")
            if vision_model_override:
                model_name = vision_model_override
            debug_print(f"OllamaProvider: Vision request detected. Using model: {model_name}. Images: {len(image_data_b64_list)}")
            # Add the images to the last user message for Ollama
            if processed_messages and image_data_b64_list:
                # Find the last user message to append images to, or the first message if no user role.
                # This assumes VisionAgent's structure where image and prompt are in the same user message.
                target_message_idx = -1
                for i in range(len(processed_messages) -1, -1, -1):
                    if processed_messages[i]["role"] == "user":
                        target_message_idx = i
                        break
                if target_message_idx != -1:
                     processed_messages[target_message_idx]["images"] = image_data_b64_list
                else: # If no user message (unlikely for vision), add to first message
                    if processed_messages:
                         processed_messages[0]["images"] = image_data_b64_list
                    else: # No messages to attach to, this is an error state
                        debug_print("OllamaProvider: Error: No messages to attach image data to.")
                        yield "Error: Could not process vision request due to message formatting issues."
                        return


        if not model_name:
            yield "Error: Ollama model not configured."
            return

        debug_print(f"OllamaProvider: Streaming chat completion with model: {model_name}, messages: {json.dumps(processed_messages, indent=2)}")

        try:
            async for part in await self.client.chat(
                model=model_name,
                messages=processed_messages,
                stream=True,
                options={
                    "temperature": config.get("temperature", LLM_PROVIDER_SETTINGS.get("ollama_default_temperature", 0.7)),
                    "num_predict": config.get("max_tokens", LLM_PROVIDER_SETTINGS.get("ollama_default_max_tokens", 4096))
                }
            ):
                if 'message' in part and 'content' in part['message']:
                    yield part['message']['content']
                if part.get('done') and part.get('error'):
                    debug_print(f"Ollama API error during streaming: {part['error']}")
                    yield f"\n[Ollama API Error: {part['error']}]"
                    break
        except httpx.ConnectError as e:
            error_msg = f"Ollama connection error: Could not connect to Ollama at {LLM_PROVIDER_SETTINGS.get('ollama_base_url')}. Ensure Ollama is running. Details: {e}"
            debug_print(error_msg)
            yield f"\n[Error: {error_msg}]"
        except ollama.ResponseError as e:
            error_msg = f"Ollama API error: {e.error} (status code: {e.status_code}). Check if model '{model_name}' is available in Ollama and supports the request."
            debug_print(error_msg)
            yield f"\n[Ollama API Error: {error_msg}]"
        except Exception as e:
            error_msg = f"Unexpected error in OllamaProvider: {type(e).__name__} - {e}"
            debug_print(error_msg)
            yield f"\n[Error: {error_msg}]"


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
