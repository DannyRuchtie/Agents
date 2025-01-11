"""Memory agent module for storing and retrieving information."""
from typing import Dict, List, Optional
import json
from pathlib import Path

from .base_agent import BaseAgent

MEMORY_SYSTEM_PROMPT = """You are a memory expert. Your role is to analyze queries 
and find relevant information from stored memories. Focus on semantic 
matching, relevance, and contextual understanding. Prioritize recent and 
highly relevant information."""

class MemoryAgent(BaseAgent):
    """Agent responsible for managing and retrieving stored information."""
    
    def __init__(self, memory_file: str = "memory.json"):
        super().__init__(
            agent_type="memory",
            system_prompt=MEMORY_SYSTEM_PROMPT,
        )
        self.memory_file = Path(memory_file)
        self.memories: Dict[str, List[str]] = self._load_memories()
    
    def _load_memories(self) -> Dict[str, List[str]]:
        """Load memories from file or initialize if not exists."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self._initialize_memories()
        return self._initialize_memories()
    
    def _initialize_memories(self) -> Dict[str, List[str]]:
        """Initialize with some example memories."""
        memories = {
            "general": [
                "The system was initialized with basic agent capabilities",
                "The system includes search, writing, code, and memory functions"
            ],
            "technical": [
                "The system uses LangChain v0.3 for agent coordination",
                "OpenAI's latest models are used for language processing"
            ]
        }
        self._save_memories(memories)
        return memories
    
    def _save_memories(self, memories: Dict[str, List[str]]) -> None:
        """Save memories to file."""
        with open(self.memory_file, 'w') as f:
            json.dump(memories, f, indent=2)
    
    async def store(self, category: str, memory: str) -> None:
        """Store a new memory.
        
        Args:
            category: Category to store the memory under
            memory: The memory text to store
        """
        if category not in self.memories:
            self.memories[category] = []
        self.memories[category].append(memory)
        self._save_memories(self.memories)
    
    async def retrieve(self, query: str, category: Optional[str] = None) -> List[str]:
        """Retrieve relevant memories based on a query.
        
        Args:
            query: The search query
            category: Optional category to search in
            
        Returns:
            List of relevant memories
        """
        # Use LLM to analyze query and find relevant memories
        search_space = (
            self.memories[category] if category and category in self.memories
            else [m for msgs in self.memories.values() for m in msgs]
        )
        
        if not search_space:
            return []
        
        # Use the LLM to rank memories by relevance
        memories_text = "\n".join(search_space)
        prompt = (
            f"Given the query: '{query}'\n"
            f"And these memories:\n{memories_text}\n"
            "Return the numbers (1-based) of the 3 most relevant memories, "
            "separated by commas. Only return the numbers."
        )
        
        response = await self.process(prompt)
        
        try:
            # Parse response and get relevant memories
            indices = [int(idx.strip()) - 1 for idx in response.split(",")]
            return [search_space[i] for i in indices if 0 <= i < len(search_space)]
        except (ValueError, IndexError):
            # Fallback to first 3 memories if parsing fails
            return search_space[:3] 