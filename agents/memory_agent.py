"""Memory agent for storing and retrieving information using JSON and LLM-based understanding."""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from .base_agent import BaseAgent
from config.paths_config import get_path, AGENTS_DOCS_DIR
from config.settings import debug_print

MEMORY_SYSTEM_PROMPT = """You are an AI assistant specialized in managing user-specific information (memories).
Your primary task is to understand user requests to STORE, RETRIEVE, UPDATE, or DELETE information from various categories.
You should also be able to infer an intent to store information from declarative statements, especially regarding personal details.

When a user interacts with you regarding their information, first determine the INTENT and extract relevant PARAMETERS.

Possible Intents and Parameters:
1.  **'store_memory'**: For when the user wants to save or remember new information. This can be explicit (e.g., "Remember my name is...") or implicit from a declarative statement (e.g., "My name is Bob." or "I live in New York.").
    *   `category` (required): Broad area like 'personal', 'projects', 'contacts', 'preferences', 'knowledge', 'schedule'. Infer this from the context. If a common PII like name, birthday, address, phone, email is mentioned, it's 'personal'. If it's about a person, it's 'contacts'. If it's about a task or goal, it's 'projects'. If it's a user preference for how the assistant should behave, it's 'preferences'. For general facts or knowledge the user wants to remember, use 'knowledge'. For events or appointments, use 'schedule'.
    *   `subcategory` (optional): More specific grouping. Examples: For 'contacts', subcategories could be 'family', 'friends', 'colleagues'. For 'preferences', 'writing_style', 'file_locations'. Infer if possible.
    *   `information` (required): The actual piece of data to be stored (e.g., "My name is Alex", "Project Phoenix deadline is next Friday", "I prefer short answers", "I live in London").
    *   `key_identifier` (optional): If the information is a specific detail about a larger topic (e.g., storing a phone number for an existing contact 'John Doe'), the key_identifier might be 'John Doe'.

2.  **'retrieve_memory'**: For when the user wants to recall stored information.
    *   `category` (optional): If the user specifies a category (e.g., "what's in my projects?", "any personal info I shared?").
    *   `subcategory` (optional): If a subcategory is specified.
    *   `query` (optional): Specific keywords or question about the memory (e.g., "my name", "Project Phoenix deadline", "my writing style preference").
    *   `key_identifier` (optional): If they are asking for a detail about a specific known entity (e.g. "what is John Doe's number?").

3.  **'update_memory'**: (Future - for now, can be treated as store, which might overwrite or add)
    *   Similar to 'store_memory', but implies changing existing information.

4.  **'delete_memory'**: (Future - not implemented yet)
    *   Parameters to identify the memory to delete.

Your response for this classification step MUST be a JSON object like:
{ "action": "<intent_name>", "parameters": { <extracted_parameters_as_key_value_pairs> } }

Example for 'remember my birthday is March 10th':
{ "action": "store_memory", "parameters": { "category": "personal", "information": "My birthday is March 10th" } }

Example for 'I am 30 years old.':
{ "action": "store_memory", "parameters": { "category": "personal", "information": "I am 30 years old." } }

Example for 'what is my name?':
{ "action": "retrieve_memory", "parameters": { "category": "personal", "query": "my name" } }

Example for 'Tell me about my family members':
{ "action": "retrieve_memory", "parameters": { "category": "contacts", "subcategory": "family" } }

Example for 'Store a note for Project Alpha: remember to call the client.':
{ "action": "store_memory", "parameters": { "category": "projects", "key_identifier": "Project Alpha", "information": "Remember to call the client." } }

If the query is ambiguous, too vague for a specific action, or asks about your capabilities as a memory agent, respond with { "action": "clarify", "parameters": { "original_query": "..." } }
Do not try to answer the memory query directly in the classification step. Just classify.
"""

class MemoryAgent(BaseAgent):
    """
    Manages long-term memory for the AI assistant, storing and retrieving user-specific
    information using a JSON file and LLM-based natural language understanding.

    Core Functionality:
    -   Stores information into categorized JSON structures.
    -   Retrieves information based on natural language queries, using LLM for intent
        parsing and basic keyword matching for retrieval.
    -   Persists memories to `memory.json`.

    LLM Usage:
    -   The `process()` method uses an LLM to interpret user queries, classify them into
        actions (store, retrieve), and extract relevant parameters.
    -   Internal methods like `store()` and `retrieve()` then use these structured parameters.
    """
    def __init__(self):
        super().__init__(
            agent_type="memory",
            system_prompt=MEMORY_SYSTEM_PROMPT
        )
        self.memory_file = AGENTS_DOCS_DIR / "memory.json"
        AGENTS_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        self.memories = self._load_memories()

    def _load_memories(self) -> Dict[str, Any]:
        """Loads memories from the JSON file, ensuring default structure."""
        if self.memory_file.exists() and self.memory_file.stat().st_size > 0:
            try:
                with open(self.memory_file, 'r') as f:
                    memories = json.load(f)
                return self._ensure_categories(memories)
            except json.JSONDecodeError:
                debug_print(f"MemoryAgent: Error decoding JSON from {self.memory_file}. Creating default structure.")
                return self._create_default_structure()
        return self._create_default_structure()

    def _create_default_structure(self) -> Dict[str, Any]:
        """Creates the default memory structure with various categories."""
        return {
            "personal": [],      # Stores dicts: {"content": str, "timestamp": str, "type": str, "key_identifier": Optional[str]}
            "contacts": {        # Stores dicts like "personal"
                "family": [], "friends": [], "colleagues": [], "other": []
            },
            "projects": [],       # Stores dicts like "personal", key_identifier can be project name
            "documents": [],      # Stores dicts like "personal", key_identifier can be document name/path
            "preferences": [],    # Stores dicts like "personal"
            "schedule": [],       # Stores dicts like "personal"
            "knowledge": [],      # Stores dicts like "personal"
            "system_notes": []   # Internal notes, errors, etc. Stores dicts like "personal"
        }

    def _ensure_categories(self, memories: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures all default categories and subcategories exist in the loaded memories."""
        default_struct = self._create_default_structure()
        for category, default_value in default_struct.items():
            if category not in memories:
                memories[category] = default_value
            elif isinstance(default_value, dict):
                if not isinstance(memories[category], dict):
                    memories[category] = default_value
                else:
                    for subcat, subcat_default_value in default_value.items():
                        if subcat not in memories[category]:
                            memories[category][subcat] = subcat_default_value
            elif not isinstance(memories[category], list):
                memories[category] = default_value
        return memories

    def _save_memories(self) -> None:
        """Saves the current memories to the JSON file."""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memories, f, indent=4)
            debug_print(f"MemoryAgent: Memories saved to {self.memory_file}")
        except Exception as e:
            debug_print(f"MemoryAgent: Error saving memories to {self.memory_file}: {str(e)}")

    async def store_memory_entry(self, category: str, information: str, subcategory: Optional[str] = None, key_identifier: Optional[str] = None) -> str:
        """Stores a new memory entry into the specified category/subcategory."""
        debug_print(f"MemoryAgent: Storing memory - Category: {category}, Subcategory: {subcategory}, Info: '{information[:50]}...', Key: {key_identifier}")
        timestamp = datetime.now().isoformat()
        
        entry_type = "general"
        if category == "personal" and any(term in information.lower() for term in ["my name is", "i am", "i'm called"]):
            entry_type = "name_identifier"
        elif category == "personal" and any(term in information.lower() for term in ["birthday", "born on"]):
            entry_type = "birthday_identifier"

        entry = {
            "content": information,
            "timestamp": timestamp,
            "type": entry_type,
            "key_identifier": key_identifier
        }

        # Ensure category exists and is of the correct type
        if category not in self.memories or \
           (isinstance(self.memories[category], dict) and subcategory is None) or \
           (isinstance(self.memories[category], list) and subcategory is not None):
            debug_print(f"MemoryAgent: Category '{category}' or subcategory '{subcategory}' structure mismatch or not found. Re-initializing category.")
            default_struct = self._create_default_structure()
            self.memories[category] = default_struct.get(category, [] if subcategory is None else {})
            if subcategory and category in self.memories and isinstance(self.memories[category], dict) and subcategory not in self.memories[category]:
                self.memories[category][subcategory] = []

        target_list = None
        if subcategory:
            if isinstance(self.memories.get(category), dict) and isinstance(self.memories[category].get(subcategory), list):
                target_list = self.memories[category][subcategory]
            else:
                debug_print(f"MemoryAgent: Subcategory {subcategory} in {category} is not a list or does not exist. Creating.")
                if not isinstance(self.memories.get(category), dict):
                    self.memories[category] = {}
                self.memories[category][subcategory] = []
                target_list = self.memories[category][subcategory]
        elif isinstance(self.memories.get(category), list):
            target_list = self.memories[category]
        else:
            debug_print(f"MemoryAgent: Category '{category}' is not a list and no subcategory provided. Cannot store.")
            return "Error: Could not store memory. Category '{category}' is not structured correctly for direct storage."

        if target_list is not None:
            # Handle overwriting specific types like 'name' in 'personal'
            if category == "personal" and entry_type == "name_identifier":
                # Remove existing name entries before adding the new one
                new_list = [e for e in target_list if e.get("type") != "name_identifier"]
                target_list.clear()
                target_list.extend(new_list)
            
            target_list.append(entry)
            self._save_memories()
            # More conversational response
            return f"Got it! I'll remember that under '{category}{f'/{subcategory}' if subcategory else ''}'."
        else:
            # Simplified complex f-string that might be causing parsing issues
            subcategory_text = f", subcategory '{subcategory}'" if subcategory else ""
            return f"Error: Could not find a valid place to store memory in category '{category}'{subcategory_text}."

    async def retrieve_memory_entries(self, category: Optional[str] = None, query: Optional[str] = None, subcategory: Optional[str] = None, key_identifier: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieves memory entries, with optional filtering and basic keyword matching."""
        debug_print(f"MemoryAgent: Retrieving memory - Category: {category}, Subcategory: {subcategory}, Query: '{query}', Key: {key_identifier}, Limit: {limit}")
        
        source_lists = []
        if category:
            if category not in self.memories:
                return []
            cat_data = self.memories[category]
            if subcategory:
                if isinstance(cat_data, dict) and subcategory in cat_data and isinstance(cat_data[subcategory], list):
                    source_lists.append(cat_data[subcategory])
                else:
                    return []
            elif isinstance(cat_data, list):
                source_lists.append(cat_data)
            elif isinstance(cat_data, dict):
                for sub_list in cat_data.values():
                    if isinstance(sub_list, list):
                        source_lists.append(sub_list)
        else:
            for cat_value in self.memories.values():
                if isinstance(cat_value, list):
                    source_lists.append(cat_value)
                elif isinstance(cat_value, dict):
                    for sub_list in cat_value.values():
                        if isinstance(sub_list, list):
                            source_lists.append(sub_list)

        all_matching_entries = []
        query_words = set(query.lower().split()) if query else set()

        for entry_list in source_lists:
            for entry in entry_list:
                if not isinstance(entry, dict):
                    continue
                
                content_match = False
                if query:
                    if any(word in entry.get("content", "").lower() for word in query_words):
                        content_match = True
                else:
                    content_match = True

                key_match = False
                if key_identifier:
                    if entry.get("key_identifier", "").lower() == key_identifier.lower():
                        key_match = True
                else:
                    key_match = True

                type_match = False
                if query and category == "personal" and any(term in query.lower() for term in ["my name", "who am i"]):
                    if entry.get("type") == "name_identifier":
                        type_match = True
                elif query and category == "personal" and "birthday" in query.lower():
                    if entry.get("type") == "birthday_identifier":
                        type_match = True
                else:
                    type_match = True

                if content_match and key_match and type_match:
                    all_matching_entries.append(entry)

        # Sort by timestamp (most recent first) and apply limit
        return sorted(all_matching_entries, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]

    async def process(self, query: str) -> str:
        debug_print(f"MemoryAgent received natural language query: {query}")
        
        # Use LLM to classify intent and extract parameters using the agent's system_prompt
        raw_classification = await super().process(query) 
        debug_print(f"MemoryAgent classification response: {raw_classification}")

        try:
            classification = json.loads(raw_classification)
            action = classification.get("action")
            params = classification.get("parameters", {})

            if action == "store_memory":
                category = params.get("category")
                information = params.get("information")
                subcategory = params.get("subcategory")
                key_identifier = params.get("key_identifier")
                
                if not category or not information:
                    return "To store something, I need to know the category and the information itself. Could you please provide that?"
                return await self.store_memory_entry(category, information, subcategory, key_identifier)
            
            elif action == "retrieve_memory":
                category = params.get("category")
                q_query = params.get("query")
                subcategory = params.get("subcategory")
                key_identifier = params.get("key_identifier")

                if not category and not q_query and not subcategory and not key_identifier:
                    return "What information are you looking for? Please specify a category, query, or identifier."
                
                retrieved_entries = await self.retrieve_memory_entries(category, q_query, subcategory, key_identifier)
                
                if not retrieved_entries:
                    specific_search = q_query or key_identifier or subcategory or category
                    criteria_text = str(specific_search) if specific_search else 'your criteria'
                    # More conversational response
                    return f"Hmm, I don't seem to have any memories matching '{criteria_text}'. You can tell me about it if you like!"
                
                # Format for presentation
                response_parts = []
                if len(retrieved_entries) == 1 and retrieved_entries[0].get("type") == "name_identifier":
                    # More conversational response
                    name_info = retrieved_entries[0]['content'].split(' is ')[-1].split(' am ')[-1].split(' called ')[-1].strip('.')
                    return f"If I remember correctly, your name is {name_info}."
                if len(retrieved_entries) == 1 and retrieved_entries[0].get("type") == "birthday_identifier":
                    # More conversational response
                    bday_info = retrieved_entries[0]['content'].split(' is ')[-1].split(' on ')[-1].strip('.')
                    return f"I believe your birthday is {bday_info}."

                for entry in retrieved_entries:
                    info = entry.get("content", "[No content]")
                    ts = entry.get("timestamp", "[No timestamp]")
                    # Simplified cat_info construction to avoid complex nested f-string
                    subcategory_info = f"/{params.get('subcategory', 'N/A')}" if params.get('subcategory') else ""
                    cat_info = f"(Category: {params.get('category', 'N/A')}{subcategory_info})"
                    response_parts.append(f"- '{info}' (Stored around: {ts.split('T')[0]}) {cat_info if category else ''}")
                
                if q_query and (q_query.lower() == "my name" or "what is my name" in q_query.lower()) and not response_parts:
                    # More conversational response
                    return "I don't seem to have your name stored. If you'd like me to remember it, just tell me by saying something like 'My name is [your name]'!"

                header_query_part = q_query or key_identifier or subcategory or category
                header = f"Here's what I found related to '{header_query_part}':\n" if header_query_part else "Here are some recent memories I have:\n"
                return header + "\n".join(response_parts)
            
            elif action == "clarify":
                original_query = params.get("original_query", query)
                # More conversational response
                return f"I'm a little unsure how to help with your memory request about '{original_query}'. Could you perhaps be more specific, or tell me what category it might fall under?"
            
            else:
                debug_print(f"MemoryAgent: Unknown action or failed to classify query: {query}. Raw: {raw_classification}")
                # More conversational response
                return "I'm not quite sure how to handle that. I can help you remember things or recall information you've told me before. For example, you can say 'Remember my favorite color is blue' or ask 'What's my favorite color?'"

        except json.JSONDecodeError:
            debug_print(f"MemoryAgent: Failed to parse JSON from LLM classification: {raw_classification}")
            # Fallback: Ask LLM to answer directly if classification fails, using a generic memory context
            fallback_prompt = f"The user asked: '{query}'. You are a memory agent. Respond helpfully based on your capabilities to store and retrieve information, even if you don't have the specific memory yet. Try to be conversational."
            return await super().process(fallback_prompt, system_prompt_override="You are a helpful memory assistant. You can store and retrieve information if the user is clear. If you don't know something, explain how the user can tell you. Please be conversational.")
        except Exception as e:
            debug_print(f"MemoryAgent: Error in process method: {type(e).__name__} - {str(e)}")
            import traceback
            debug_print(traceback.format_exc())
            return f"I encountered an unexpected issue while trying to process your memory request: {str(e)}"

    # --- Potentially deprecate or refine older direct methods if process() becomes robust --- 
    async def store(self, category: str, information: str, subcategory: str | None = None) -> str:
        """Directly store information. Consider using 'process' for NL queries."""
        debug_print(f"MemoryAgent: Direct store called - Category: {category}, Subcategory: {subcategory}, Info: '{information[:50]}...'")
        return await self.store_memory_entry(category, information, subcategory)

    async def retrieve(self, category: Optional[str] = None, query: str | None = None, subcategory: str | None = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Directly retrieve information. Consider using 'process' for NL queries."""
        debug_print(f"MemoryAgent: Direct retrieve called - Category: {category}, Subcategory: {subcategory}, Query: '{query}'")
        return await self.retrieve_memory_entries(category, query, subcategory, limit=limit)

    async def get_family_members(self) -> List[str]:
        """Helper method to retrieve all family members' 'content'."""
        debug_print("MemoryAgent: Getting family members.")
        family_entries = await self.retrieve_memory_entries(category="contacts", subcategory="family", limit=100)
        return [entry.get("content", "") for entry in family_entries if entry.get("content")]

    async def get_timestamp(self, category: str, content_query: str, subcategory: Optional[str]=None) -> Optional[str]:
        """Get the timestamp for when a specific memory (by content query) was stored."""
        debug_print(f"MemoryAgent: Getting timestamp - Category: {category}, Subcategory: {subcategory}, Content query: '{content_query}'")
        # Search for entries matching the content query within the category/subcategory
        # This uses retrieve_memory_entries for its filtering logic
        matched_entries = await self.retrieve_memory_entries(category=category, query=content_query, subcategory=subcategory, limit=1)
        if matched_entries and matched_entries[0].get("content", "").lower().strip() == content_query.lower().strip():
            return matched_entries[0].get("timestamp")
        return None 