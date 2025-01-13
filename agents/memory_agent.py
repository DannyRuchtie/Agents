"""Memory agent for storing and retrieving information."""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from .base_agent import BaseAgent
from config.paths_config import get_path, AGENTS_DOCS_DIR

class MemoryAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_type="memory",
            system_prompt="You are a memory management expert."
        )
        self.memory_file = AGENTS_DOCS_DIR / "memory.json"
        self.memories = self._load_memories()

    def _load_memories(self) -> Dict[str, Any]:
        if self.memory_file.exists():
            with open(self.memory_file, 'r') as f:
                try:
                    memories = json.load(f)
                    # Ensure all required categories exist
                    return self._ensure_categories(memories)
                except json.JSONDecodeError:
                    return self._create_default_structure()
        return self._create_default_structure()

    def _create_default_structure(self) -> Dict[str, Any]:
        """Create the default memory structure."""
        return {
            "personal": [],  # Names, preferences, important dates
            "contacts": {  # Family, friends, colleagues
                "family": [],  # Immediate family members
                "friends": [],
                "colleagues": [],
                "other": []
            },
            "projects": [],  # Current and past projects, tasks, goals
            "documents": [],  # Created documents, their locations, and summaries
            "preferences": {  # User preferences for system behavior
                "writing_style": [],
                "file_locations": [],
                "ui_preferences": []
            },
            "schedule": [],  # Meetings, deadlines, events
            "knowledge": {  # User's domain knowledge and interests
                "technical": [],
                "interests": [],
                "learning": []
            },
            "system": {  # System-related information
                "config": [],
                "history": [],
                "errors": []
            }
        }

    def _ensure_categories(self, memories: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required categories exist in the memories."""
        default = self._create_default_structure()
        for category, value in default.items():
            if category not in memories:
                memories[category] = value
            elif isinstance(value, dict):
                for subcategory in value:
                    if subcategory not in memories[category]:
                        memories[category][subcategory] = []
        return memories

    async def store(self, category: str, information: str, subcategory: str | None = None) -> None:
        """Store information in the specified category and optional subcategory."""
        timestamp = datetime.now().isoformat()
        entry = {
            "content": information,
            "timestamp": timestamp,
            "type": "name" if any(word in information.lower() for word in ["my name is", "i am", "i'm"]) else "general"
        }
        
        # Special handling for family information
        if any(word in information.lower() for word in ["son", "daughter", "wife", "husband", "children"]):
            category = "contacts"
            subcategory = "family"
        
        try:
            if subcategory:
                if isinstance(self.memories[category], dict):
                    if subcategory not in self.memories[category]:
                        self.memories[category][subcategory] = []
                    self.memories[category][subcategory].append(entry)
            else:
                if isinstance(self.memories[category], list):
                    # For personal category, update existing name entry if this is a name
                    if category == "personal" and entry["type"] == "name":
                        # Remove old name entries
                        self.memories[category] = [e for e in self.memories[category] if e.get("type") != "name"]
                    self.memories[category].append(entry)
            
            self._save_memories()
        except Exception as e:
            print(f"Error storing memory: {str(e)}")
            raise

    async def retrieve(self, category: str, query: str | None = None, subcategory: str | None = None, limit: int = 5) -> List[str]:
        """Retrieve information from memory, optionally filtered by category, subcategory, and query."""
        try:
            if category not in self.memories:
                return []

            if subcategory:
                if isinstance(self.memories[category], dict) and subcategory in self.memories[category]:
                    entries = self.memories[category][subcategory]
                else:
                    return []
            else:
                entries = self.memories[category] if isinstance(self.memories[category], list) else []

            # For personal category, return the content of entries
            if category == "personal":
                return [entry["content"] for entry in entries]

            # For family queries, combine information
            if category == "contacts" and subcategory == "family":
                family_info = [entry["content"] for entry in entries]
                if family_info:
                    return [" Also, ".join(family_info)]
                return []

            # If no query, return most recent entries
            if not query:
                return [entry["content"] for entry in sorted(entries, key=lambda x: x["timestamp"], reverse=True)[:limit]]

            # If query exists, check for semantic similarity
            matched_entries = []
            query_words = set(query.lower().split())
            for entry in entries:
                content = entry["content"].lower()
                # Check if any query word is in the content
                if any(word in content for word in query_words):
                    matched_entries.append(entry["content"])
                    if len(matched_entries) >= limit:
                        break
            
            return matched_entries

        except Exception as e:
            print(f"Error retrieving memory: {str(e)}")
            return []

    def _save_memories(self) -> None:
        """Save memories to file."""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memories, f, indent=2)
        except Exception as e:
            print(f"Error saving memories: {str(e)}")
            raise

    async def get_family_members(self) -> List[str]:
        """Helper method to retrieve all family members."""
        try:
            return await self.retrieve("contacts", subcategory="family")
        except Exception as e:
            print(f"Error retrieving family members: {str(e)}")
            return [] 