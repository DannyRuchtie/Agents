"""Auto Model Selector for intelligent model routing based on task complexity.

Based on: https://community.openai.com/t/automatic-model-selection-for-improved-efficiency-and-sustainability/1151680
"""

import re
from typing import Dict, Literal
from config.settings import MODEL_SELECTOR_SETTINGS, LLM_PROVIDER_SETTINGS, debug_print

ComplexityLevel = Literal["simple", "moderate", "complex", "reasoning", "vision", "realtime"]


class TaskComplexityClassifier:
    """Classifies task complexity based on prompt analysis."""
    
    def __init__(self):
        self.settings = MODEL_SELECTOR_SETTINGS
        self.simple_threshold = self.settings["complexity_threshold_tokens"]["simple"]
        self.complex_threshold = self.settings["complexity_threshold_tokens"]["complex"]
        self.simple_keywords = self.settings["complexity_keywords"]["simple"]
        self.complex_keywords = self.settings["complexity_keywords"]["complex"]
    
    def classify_prompt(self, prompt: str, task_type: str = "text") -> ComplexityLevel:
        """Classify a prompt's complexity level.
        
        Args:
            prompt: The user's query/prompt
            task_type: Type of task - "text", "vision", "realtime"
            
        Returns:
            ComplexityLevel: One of "simple", "moderate", "complex", "reasoning", "vision", "realtime"
        """
        # Handle special task types first
        if task_type == "vision":
            return "vision"
        
        if task_type == "realtime":
            return "realtime"
        
        # Normalize prompt for analysis
        text = prompt.lower()
        tokens = len(text.split())
        
        debug_print(f"ModelSelector: Analyzing prompt with {tokens} tokens")
        
        # Check for complex indicators (highest priority)
        for pattern in self.complex_keywords:
            if re.search(pattern, text):
                debug_print(f"ModelSelector: Found complex indicator '{pattern}' - routing to complex model")
                return "complex"
        
        # Check for reasoning tasks that need o1
        reasoning_indicators = [
            r"prove",
            r"derive mathematically",
            r"logical proof",
            r"theorem",
            r"solve this problem step by step",
            r"multi-step reasoning",
            r"complex calculation"
        ]
        for pattern in reasoning_indicators:
            if re.search(pattern, text):
                debug_print(f"ModelSelector: Found reasoning indicator '{pattern}' - routing to reasoning model")
                return "reasoning"
        
        # Check for simple indicators
        for pattern in self.simple_keywords:
            if re.search(pattern, text):
                # Only classify as simple if also short enough
                if tokens < self.simple_threshold:
                    debug_print(f"ModelSelector: Found simple indicator '{pattern}' and short length - routing to simple model")
                    return "simple"
        
        # Fallback based on length
        if tokens > self.complex_threshold:
            debug_print(f"ModelSelector: Long prompt ({tokens} tokens) - routing to complex model")
            return "complex"
        elif tokens > self.simple_threshold:
            debug_print(f"ModelSelector: Medium prompt ({tokens} tokens) - routing to moderate model")
            return "moderate"
        else:
            debug_print(f"ModelSelector: Short prompt ({tokens} tokens) with no indicators - routing to simple model")
            return "simple"


class ModelSelector:
    """Selects the most appropriate model based on task complexity."""
    
    def __init__(self):
        self.settings = MODEL_SELECTOR_SETTINGS
        self.classifier = TaskComplexityClassifier()
        self.enabled = self.settings.get("enabled", True)
    
    def select_model(self, prompt: str, task_type: str = "text") -> Dict[str, str]:
        """Select the most appropriate model for a given prompt and task type.
        
        Args:
            prompt: The user's query/prompt
            task_type: Type of task - "text", "vision", "realtime"
            
        Returns:
            Dict with keys:
                - provider: "openai" or "ollama"
                - model: The specific model name to use
                - complexity: The determined complexity level
        """
        if not self.enabled:
            # If model selector is disabled, return default
            debug_print("ModelSelector: Disabled, using default model")
            return {
                "provider": "openai",
                "model": self.settings["simple_model"],
                "complexity": "simple"
            }
        
        # Classify the task complexity
        complexity = self.classifier.classify_prompt(prompt, task_type)
        
        # Select model based on complexity
        if complexity == "simple":
            # Option to use Ollama for cost savings
            if self.settings.get("use_ollama_for_simple", False):
                model_name = LLM_PROVIDER_SETTINGS.get("ollama_default_model")
                if not model_name:
                    debug_print("ModelSelector: ollama_default_model not set; falling back to OpenAI simple model")
                    model = {
                        "provider": "openai",
                        "model": self.settings["simple_model"],
                        "complexity": complexity
                    }
                else:
                    model = {
                        "provider": "ollama",
                        "model": model_name,
                        "complexity": complexity
                    }
            else:
                model = {
                    "provider": "openai",
                    "model": self.settings["simple_model"],
                    "complexity": complexity
                }
        
        elif complexity == "moderate":
            model = {
                "provider": "openai",
                "model": self.settings["moderate_model"],
                "complexity": complexity
            }
        
        elif complexity == "complex":
            model = {
                "provider": "openai",
                "model": self.settings["complex_model"],
                "complexity": complexity
            }
        
        elif complexity == "reasoning":
            model = {
                "provider": "openai",
                "model": self.settings["reasoning_model"],
                "complexity": complexity
            }
        
        elif complexity == "vision":
            model = {
                "provider": "openai",
                "model": self.settings["vision_model"],
                "complexity": complexity
            }
        
        elif complexity == "realtime":
            model = {
                "provider": "openai",
                "model": self.settings["realtime_model"],
                "complexity": complexity
            }
        
        else:
            # Fallback to moderate
            debug_print(f"ModelSelector: Unknown complexity '{complexity}', using moderate model")
            model = {
                "provider": "openai",
                "model": self.settings["moderate_model"],
                "complexity": "moderate"
            }
        
        debug_print(f"ModelSelector: Selected {model['model']} (complexity: {complexity})")
        return model
    
    def get_model_for_agent(self, agent_type: str, prompt: str = "") -> Dict[str, str]:
        """Get the appropriate model for a specific agent type.
        
        This method provides agent-specific model selection logic.
        
        Args:
            agent_type: The type of agent (e.g., "search", "email", "screen")
            prompt: The user's query/prompt (optional, for context)
            
        Returns:
            Dict with provider and model information
        """
        # Agent-specific routing
        if agent_type == "screen":
            return self.select_model(prompt, task_type="vision")
        
        elif agent_type in ["browser"]:
            # Browser tasks may involve vision
            if "screenshot" in prompt.lower() and ("describe" in prompt.lower() or "what" in prompt.lower()):
                return self.select_model(prompt, task_type="vision")
            else:
                return self.select_model(prompt, task_type="text")
        
        elif agent_type in ["email", "reminders"]:
            # These agents typically need simple classification
            return {
                "provider": "openai",
                "model": self.settings["simple_model"],
                "complexity": "simple"
            }
        
        elif agent_type == "search":
            # Search queries vary in complexity
            return self.select_model(prompt, task_type="text")
        
        elif agent_type == "personality":
            # Personality analysis is moderate complexity
            return {
                "provider": "openai",
                "model": self.settings["moderate_model"],
                "complexity": "moderate"
            }
        
        elif agent_type == "realtime":
            return {
                "provider": "openai",
                "model": self.settings["realtime_model"],
                "complexity": "realtime"
            }
        
        else:
            # Default: analyze the prompt
            return self.select_model(prompt, task_type="text")


# Global instance for easy access
_model_selector_instance = None


def get_model_selector() -> ModelSelector:
    """Get the global ModelSelector instance (singleton pattern)."""
    global _model_selector_instance
    if _model_selector_instance is None:
        _model_selector_instance = ModelSelector()
    return _model_selector_instance
