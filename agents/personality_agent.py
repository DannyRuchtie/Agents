"""Personality agent for learning and adapting to user's traits and preferences."""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import re

from .base_agent import BaseAgent
from .memory_agent import MemoryAgent
from config.settings import PERSONALITY_TRAITS, PERSONALITY_SETTINGS, save_settings, is_debug_mode, debug_print
from config.paths_config import AGENTS_DOCS_DIR

class PersonalityAgent(BaseAgent):
    """Agent that learns and adapts to user's personality."""
    
    def __init__(self):
        """Initialize the personality agent."""
        super().__init__(
            agent_type="personality",
            system_prompt="You are an expert in understanding human personality and behavior patterns."
        )
        self.personality_file = AGENTS_DOCS_DIR / "personality.json"
        self.traits = self._load_traits()
        self.memory_agent = MemoryAgent()
        
    def _load_traits(self) -> Dict[str, Any]:
        """Load personality traits from file or create default."""
        if self.personality_file.exists():
            with open(self.personality_file, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return PERSONALITY_TRAITS.copy()
        return PERSONALITY_TRAITS.copy()
        
    def _save_traits(self) -> None:
        """Save personality traits to file."""
        with open(self.personality_file, 'w') as f:
            json.dump(self.traits, f, indent=2)
            
    async def analyze_interaction(self, query: str, response: str) -> None:
        """Analyze user interaction to update personality traits."""
        try:
            # Update interaction history
            timestamp = datetime.now().isoformat()
            if "interaction_history" not in self.traits:
                self.traits["interaction_history"] = []
            
            self.traits["interaction_history"].append({
                "timestamp": timestamp,
                "user_input": query,
                "assistant_response": response
            })
            
            # Analyze communication style
            self._analyze_communication_style(query)
            
            # Analyze interests and preferences
            self._analyze_interests(query)
            
            # Update personality traits
            self._update_personality_traits()
            
            # Save changes
            self._save_traits()
            
            # Store personality insights in memory
            await self._store_personality_insights()
            
        except Exception as e:
            debug_print(f"Error analyzing interaction: {str(e)}")
            
    def _analyze_communication_style(self, text: str):
        """Analyze communication style from text."""
        # Check formality level
        formal_indicators = len(re.findall(r'\b(please|thank you|kindly|would you|could you)\b', text.lower()))
        informal_indicators = len(re.findall(r'\b(hey|hi|yeah|cool|awesome|great)\b', text.lower()))
        
        # Check humor level
        humor_indicators = len(re.findall(r'\b(haha|lol|funny|😂|😆|🤣)\b', text.lower()))
        
        # Check emoji usage
        emoji_count = len(re.findall(r'[\U0001F300-\U0001F9FF]', text))
        
        # Update communication style
        if "communication_style" not in self.traits:
            self.traits["communication_style"] = {}
            
        style = self.traits["communication_style"]
        style["formality_level"] = "formal" if formal_indicators > informal_indicators else "informal"
        style["humor_level"] = min(10, humor_indicators * 2)  # Scale 0-10
        style["emoji_usage"] = min(10, emoji_count * 2)  # Scale 0-10
        
        # Update global settings
        PERSONALITY_SETTINGS["humor_level"] = style["humor_level"]
        PERSONALITY_SETTINGS["formality_level"] = style["formality_level"]
        PERSONALITY_SETTINGS["emoji_usage"] = style["emoji_usage"]
        save_settings()
        
    def _analyze_interests(self, text: str):
        """Analyze and track user interests from text."""
        if "interests" not in self.traits:
            self.traits["interests"] = {}
            
        # Define interest categories and their keywords
        interest_categories = {
            "technology": r'\b(computer|programming|software|hardware|tech|AI|coding)\b',
            "science": r'\b(science|physics|chemistry|biology|research|experiment)\b',
            "arts": r'\b(art|music|painting|drawing|creative|design)\b',
            "sports": r'\b(sports|exercise|fitness|game|team|play|workout)\b',
            "business": r'\b(business|work|job|career|professional|company)\b',
            "entertainment": r'\b(movie|show|series|book|story|watch|read)\b'
        }
        
        # Count mentions of each category
        for category, pattern in interest_categories.items():
            mentions = len(re.findall(pattern, text.lower()))
            if mentions > 0:
                self.traits["interests"][category] = \
                    self.traits["interests"].get(category, 0) + mentions
                    
    def _update_personality_traits(self):
        """Update personality traits based on interaction history."""
        if "traits" not in self.traits:
            self.traits["traits"] = {
                "openness": 5,
                "conscientiousness": 5,
                "extraversion": 5,
                "agreeableness": 5,
                "neuroticism": 5
            }
            
        # Update traits based on recent interactions
        history = self.traits.get("interaction_history", [])
        if history:
            recent = history[-10:]  # Look at last 10 interactions
            
            # Analyze patterns in recent interactions
            total_words = sum(len(i["user_input"].split()) for i in recent)
            avg_response_length = total_words / len(recent)
            
            # Update traits based on interaction patterns
            traits = self.traits["traits"]
            
            # Extraversion - based on conversation engagement
            traits["extraversion"] = min(10, max(1, int(avg_response_length / 10)))
            
            # Update global personality traits
            PERSONALITY_TRAITS.update(self.traits["traits"])
            save_settings()
            
    async def _store_personality_insights(self) -> None:
        """Store personality insights in memory."""
        insights = []
        
        # Generate insights based on traits
        if self.traits["communication_style"]["formality_level"] < 0.4:
            insights.append("Prefers casual, relaxed communication")
        elif self.traits["communication_style"]["formality_level"] > 0.7:
            insights.append("Appreciates formal, professional communication")
            
        if self.traits["communication_style"]["verbosity"] < 0.4:
            insights.append("Prefers concise, direct responses")
        elif self.traits["communication_style"]["verbosity"] > 0.7:
            insights.append("Enjoys detailed, comprehensive responses")
            
        if self.traits["interests"]:
            insights.append(f"Shows interest in: {', '.join(self.traits['interests'])}")
            
        # Store insights in memory
        if insights:
            await self.memory_agent.store(
                category="personal",
                content={"type": "personality_insight", "insights": insights}
            )
            
    async def get_interaction_style(self) -> Dict[str, Any]:
        """Get the current interaction style preferences."""
        return {
            "formality": self.traits["communication_style"]["formality_level"],
            "verbosity": self.traits["communication_style"]["verbosity"],
            "humor": self.traits["communication_style"]["humor_level"],
            "emoji_usage": self.traits["communication_style"]["emoji_usage"],
            "interests": self.traits["interests"],
            "technical_level": self.traits["preferences"]["technical_level"]
        }
        
    async def get_personality_prompt(self) -> str:
        """Generate a personality-aware system prompt."""
        style = await self.get_interaction_style()
        
        prompt_parts = [
            f"Interact in a {'casual and friendly' if style['formality'] < 0.5 else 'professional but warm'} way",
            f"Keep responses {'concise and direct' if style['verbosity'] < 0.5 else 'detailed and comprehensive'}",
            f"Use {'frequent' if style['humor'] > 0.6 else 'occasional'} humor",
            f"{'Use emojis to express emotion' if style['emoji_usage'] else 'Keep responses emoji-free'}",
        ]
        
        if style["interests"]:
            prompt_parts.append(f"Reference shared interests when relevant: {', '.join(style['interests'])}")
            
        prompt_parts.append(f"Maintain {style['technical_level']} technical detail level")
        
        return " | ".join(prompt_parts) 