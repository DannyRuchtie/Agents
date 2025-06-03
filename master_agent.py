import json
import datetime
import os
import re
from typing import Optional # Added for type hinting

print("!!!!!! MASTER_AGENT.PY MODULE LOADED - VERSION: TOP_LEVEL_DEBUG_V4 !!!!!!")

from agents.base_agent import BaseAgent # Assuming BaseAgent is in agents.base_agent
from agents.search_agent import SearchAgent
from agents.email_agent import EmailAgent
from agents.calculator_agent import CalculatorAgent
from agents.weather_agent import WeatherAgent
from agents.vision_agent import VisionAgent # Added
from agents.camera_agent import CameraAgent # Added
from agents.browser_agent import BrowserAgent # Added for browser automation
# ScreenAgent import - ensure this is correct based on your project structure
# from agents.screen_agent import ScreenAgent # Assuming you have this or similar

from config.settings import debug_print # Assuming debug_print is in config.settings

MEMORY_FILE_PATH = "agent_memory.json"

# Define REGEX patterns for hardcoded browser triggers
# These will be checked BEFORE LLM routing for specific browser commands.
# Adjusted regex to be more specific and capture common phrasings.
BROWSER_TRIGGER_PATTERNS = [
    # Screenshot specific websites (more robust for URLs/domains)
    re.compile(r"^(take a screenshot of|screenshot|capture screen of|capture|make screenshot of)\s+(https?://\S+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(.*)$", re.IGNORECASE),
    # Go to/open/browse/navigate to a website (and potentially do something, like screenshot)
    re.compile(r"^(go to|open|browse to|navigate to)\s+(https?://\S+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(.*)$", re.IGNORECASE),
    # Scrape data from/on a specific website - Updated for more flexibility
    re.compile(r"^(scrape|scraping)\s+(?:.*?\s+)?(https?://\S+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", re.IGNORECASE),
    # Fill form on a specific website (basic trigger, actual filling depends on browser-use capability)
    re.compile(r"^(fill.*?form on|enter data on)\s+(https?://\S+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(.*)$", re.IGNORECASE),
]

MASTER_SYSTEM_PROMPT = """You are a master AI agent coordinating a team of specialized AI agents.
Your primary role is to understand the user's request, current conversation history, and route it to the most appropriate specialized agent.

**Hardcoded Triggers:** Many common browser commands (screenshots of websites, go to URL, scrape specific site) are handled by hardcoded logic. The LLM routing below is for other cases.

Available agents and their functions (for LLM routing if no hardcoded trigger matches):
- search: For general web searches, finding information, or answering questions when a specific URL is NOT provided.
- browser: For more nuanced or complex direct interactions with specific websites that ARE NOT covered by hardcoded triggers. Examples: complex multi-step interactions on a single page after initial navigation.
- screen: Use ONLY to capture and describe the user's **CURRENT ENTIRE LIVE SCREEN**. **NEVER use if a specific website/URL is mentioned for a screenshot (that's 'browser' agent, likely via hardcoded logic).**
- email: For managing Gmail.
- calculator: For mathematical calculations.
- camera: For capturing images from the webcam.
- weather: For fetching current weather information.
- writer: For creative writing tasks.
- memory: For remembering and retrieving information.

Routing and Information Extraction (LLM Fallback - after hardcoded checks):
If no hardcoded trigger matches, determine the best agent. Your response MUST be a single, valid JSON object.
{
  "route_to_agent": "agent_name",
  "action_type": "specific_action", // Optional
  "parameters": { "query_for_agent": "full user query or modified query" },
  "explanation": "Brief explanation of why this agent and action were chosen."
}

**User Agent Preference:** If the user explicitly states 'use [agent_name] agent to [task]' (e.g., 'use browser agent to scrape example.com'), and the task is appropriate for that agent, prioritize routing to that specified agent.

CRITICAL OVERRIDE (Webcam - LLM Fallback): For webcam queries (e.g., "can you see me?"), if not caught by other logic, route to 'camera'.

Parameter Passing:
- For 'search', 'browser', 'screen', 'calculator', 'weather', 'camera', 'writer': pass "query_for_agent".
- For 'email': extract 'to', 'subject', 'body' or 'search_terms'.

Use conversation history for context. Prioritize direct agent routing based on explicit distinctions.
If no agent clearly fits (and no hardcoded trigger/critical directive applies), use "master_agent_direct".
"""

class MasterAgent(BaseAgent):
    def __init__(self, file_path_expert=None):
        super().__init__(agent_type="master", system_prompt=MASTER_SYSTEM_PROMPT)
        self.conversation_history = []
        self.file_path_expert = file_path_expert
        # Initialize specialized agents
        self.search_agent = SearchAgent()
        self.email_agent = EmailAgent()
        self.calculator_agent = CalculatorAgent()
        self.vision_agent = VisionAgent() 
        self.camera_agent = CameraAgent(vision_agent=self.vision_agent) 
        self.browser_agent = BrowserAgent()
        # self.screen_agent = ScreenAgent() # Make sure ScreenAgent is initialized if you have it
        self._load_memory_file() 
        self.weather_agent = WeatherAgent(memory_data_ref=self.memory_data) 
        # self.memory_agent = MemoryAgent() # If we create a dedicated class

    def _load_memory_file(self):
        try:
            if os.path.exists(MEMORY_FILE_PATH):
                with open(MEMORY_FILE_PATH, 'r') as f:
                    self.memory_data = json.load(f)
                debug_print(f"MasterAgent: Loaded memory from {MEMORY_FILE_PATH}")
            else:
                self.memory_data = {} # Initialize if file doesn't exist
                debug_print(f"MasterAgent: Memory file {MEMORY_FILE_PATH} not found, initialized empty memory.")
        except Exception as e:
            debug_print(f"MasterAgent: Error loading memory file {MEMORY_FILE_PATH}: {e}")
            self.memory_data = {} # Initialize on error

    def _persist_memory_item(self, category: str, item_content: any, is_fact_store_item: bool = False):
        if not isinstance(self.memory_data, dict): # Ensure memory_data is a dict
            self.memory_data = {}
        
        if category not in self.memory_data:
            self.memory_data[category] = []
        
        if category == "conversation_history":
             self.memory_data[category] = item_content # Replace if it's the whole history
        elif is_fact_store_item: # item_content is already the dict with entity, attribute, value
            if isinstance(self.memory_data[category], list):
                # Optional: Check for duplicates/updates for the same entity-attribute pair
                # For simplicity now, just append.
                self.memory_data[category].append({
                    "timestamp": datetime.datetime.now().isoformat(),
                    **item_content # spread the dict here
                })
            else: # If the category exists but isn't a list, reinitialize it as a list
                debug_print(f"MasterAgent: Warning - category '{category}' in memory was not a list. Reinitializing.")
                self.memory_data[category] = [{
                    "timestamp": datetime.datetime.now().isoformat(),
                    **item_content
                }]
        elif isinstance(self.memory_data[category], list):
            self.memory_data[category].append({
                "timestamp": datetime.datetime.now().isoformat(),
                "content": item_content
            })
        else: # If the category exists but isn't a list, reinitialize it as a list
             debug_print(f"MasterAgent: Warning - category '{category}' in memory was not a list. Reinitializing.")
             self.memory_data[category] = [{
                "timestamp": datetime.datetime.now().isoformat(),
                "content": item_content
            }]

        try:
            with open(MEMORY_FILE_PATH, 'w') as f:
                json.dump(self.memory_data, f, indent=2)
            debug_print(f"MasterAgent: Persisted item to memory category '{category}' in {MEMORY_FILE_PATH}")
        except Exception as e:
            debug_print(f"MasterAgent: Error persisting memory to {MEMORY_FILE_PATH}: {e}")

    async def process(self, user_input: str, local_file_content: Optional[str] = None) -> str:
        debug_print("MasterAgent.process -- TOP OF METHOD -- VERSION CHECKPOINT: HARDCODED_BROWSER_TRIGGERS_V3_FORCE_ROUTE")
        self.conversation_history.append({"role": "user", "content": user_input})

        agent_choice = None
        action_type = None
        parameters = {}
        query_for_agent = user_input # Default query for agent

        # --- Hardcoded Browser Agent Triggers ---
        hardcoded_route_to_browser = False
        stripped_user_input = user_input.strip()
        debug_print(f"MasterAgent: Evaluating for hardcoded triggers. Input to match: '{stripped_user_input}'")
        
        for i, pattern in enumerate(BROWSER_TRIGGER_PATTERNS):
            debug_print(f"MasterAgent: Checking pattern #{i+1}: {pattern.pattern}")
            match = pattern.match(stripped_user_input)
            if match:
                debug_print(f"MasterAgent: SUCCESS - Hardcoded trigger matched! Pattern: {pattern.pattern}")
                agent_choice = "browser"
                action_type = "direct_browser_command" 
                parameters = {"query_for_agent": stripped_user_input} 
                query_for_agent = stripped_user_input # Ensure query_for_agent is set
                hardcoded_route_to_browser = True
                break
        # --- End Hardcoded Browser Agent Triggers ---

        if not hardcoded_route_to_browser:
            debug_print("MasterAgent: No hardcoded browser trigger matched. Proceeding with LLM routing.")
            routing_prompt_addition = "Current conversation history (last few turns):\n"
            for entry in self.conversation_history[-5:]: 
                routing_prompt_addition += f"{entry['role']}: {entry['content']}\n"
            
            if local_file_content:
                routing_prompt_addition += f"\nUser has also provided content from a local file: {local_file_content[:500]}..." 

            try:
                action_details_json_str = await super().process(f"{routing_prompt_addition}\n\nUser Query: {user_input}")
                debug_print(f"MasterAgent: LLM routing/action decision: {action_details_json_str}")
                
                action_details = None
                try:
                    action_details = json.loads(action_details_json_str)
                except json.JSONDecodeError:
                    json_match = re.search(r'\{.*?\}', action_details_json_str, re.DOTALL)
                    if json_match:
                        try:
                            action_details = json.loads(json_match.group(0))
                            debug_print(f"MasterAgent: Extracted JSON: {action_details}")
                        except json.JSONDecodeError as e_inner:
                            debug_print(f"MasterAgent: Failed to parse extracted JSON: {e_inner}")
                    else:
                        debug_print("MasterAgent: No JSON object found in LLM output.")

                if action_details:
                    agent_choice = action_details.get("route_to_agent")
                    action_type = action_details.get("action_type")
                    parameters = action_details.get("parameters", {})
                    query_for_agent = parameters.get("query_for_agent", user_input)
                else: # Fallback if JSON parsing failed or action_details is None
                    simple_route_match = re.match(r'^(?:ROUTE:\s*)?(\w+)', action_details_json_str.strip(), re.IGNORECASE)
                    if simple_route_match:
                        agent_name_from_simple_route = simple_route_match.group(1).lower()
                        known_agents = ["search", "email", "calculator", "camera", "weather", "memory", "master_agent_direct", "browser", "screen", "writer"]
                        if agent_name_from_simple_route in known_agents:
                            agent_choice = agent_name_from_simple_route
                            parameters = {"query_for_agent": user_input}
                            query_for_agent = user_input
                            action_type = "simple_route_match"
                            debug_print(f"MasterAgent: Interpreted simple route from LLM output: {agent_choice}")
                        else:
                            debug_print(f"MasterAgent: Simple route '{agent_name_from_simple_route}' not in known_agents. Falling back.")
                            agent_choice = "master_agent_direct"
                            action_type = "unknown_simple_route_fallback"
                            query_for_agent = user_input
                    else:
                        debug_print("MasterAgent: LLM failed to provide valid JSON or simple route. Falling back to master agent direct.")
                        agent_choice = "master_agent_direct"
                        action_type = "llm_parse_failure_fallback"
                        query_for_agent = user_input

            except Exception as e:
                debug_print(f"Error during LLM routing in MasterAgent.process: {e}")
                agent_choice = "master_agent_direct"
                action_type = "llm_exception_fallback"
                query_for_agent = user_input
        
        # Ensure query_for_agent is set if parameters came from hardcoded route but didn't explicitly set it
        if hardcoded_route_to_browser and "query_for_agent" not in parameters:
             parameters["query_for_agent"] = stripped_user_input
             query_for_agent = stripped_user_input
        elif "query_for_agent" not in parameters: # General fallback for query_for_agent
            parameters["query_for_agent"] = user_input
            query_for_agent = user_input
        else: # If parameters["query_for_agent"] exists, ensure query_for_agent var is synced
            query_for_agent = parameters["query_for_agent"]

        # --- Hardcoded override for camera queries (if not already hardcoded to browser) ---
        if not hardcoded_route_to_browser: 
            normalized_user_input_cam = user_input.strip().lower()
            camera_trigger_phrases = [
                "can you see me", "can u see me", "see me",
                "look at me", "what do i look like", 
                "use the camera", "activate camera", "show me what you see",
                "whats on camera", "whats in front of me"
            ]
            normalized_user_input_no_punctuation_cam = normalized_user_input_cam.replace('?', '').replace('!', '').replace('.', '')
            for phrase in camera_trigger_phrases:
                if phrase in normalized_user_input_no_punctuation_cam:
                    if agent_choice != "camera":
                        debug_print(f"MasterAgent: Hardcoded override to 'camera' agent (from LLM path) due to phrase: '{phrase}'. Original LLM/Hardcoded route: '{agent_choice}'.")
                        agent_choice = "camera"
                        query_for_agent = "User asked to use the camera or a related query: " + user_input
                        parameters["query_for_agent"] = query_for_agent
                        action_type = "direct_camera_command_override"
                    break 

        response_content = f"Could not route request. Agent choice: '{agent_choice}', Action: '{action_type}' (Query: '{query_for_agent}')"

        # --- Context Injection from Fact Store (Phase 2) ---
        if agent_choice in ["email", "search", "browser"]: # Added browser to context injection if applicable
            if "fact_store" in self.memory_data:
                augmented_query = query_for_agent
                facts_used_for_augmentation = [] 
                for fact in self.memory_data["fact_store"]:
                    entity_name = fact.get("entity")
                    entity_value = fact.get("value")
                    # Ensure we have an entity name and it hasn't been used for this query augmentation yet
                    # and we are not trying to augment based on a generic "user" entity in this particular loop.
                    if entity_name and entity_name not in facts_used_for_augmentation and entity_name.lower() != "user": 
                        import re # Moved import inside to ensure it's only used when needed and avoid potential module-level clutter if not universally used.
                        try:
                            # Attempt to find the entity as a whole word, case insensitive
                            if re.search(r"\b" + re.escape(entity_name) + r"\b", augmented_query, re.IGNORECASE):
                                # Simple augmentation: replace entity with "entity (value)"
                                replacement_text = f"{entity_name} ({entity_value})"
                                # Perform case-insensitive replacement of the first occurrence
                                augmented_query = re.sub(r"\b" + re.escape(entity_name) + r"\b", replacement_text, augmented_query, 1, re.IGNORECASE)
                                facts_used_for_augmentation.append(entity_name)
                                debug_print(f"MasterAgent: Augmented query with fact: '{entity_name}' -> '{replacement_text}'. New query: '{augmented_query}'")
                        except re.error as e:
                            debug_print(f"MasterAgent: Regex error during fact augmentation for entity '{entity_name}': {e}")
                
                if augmented_query != query_for_agent:
                    query_for_agent = augmented_query 
        
        # Removed the specific default location injection block for WeatherAgent from here,
        # as WeatherAgent now handles its own default location lookup using the passed memory_data_ref.

        # --- Specific override for "remember this" --- 
        if agent_choice == "memory" and user_input.strip().lower() == "remember this":
            action_type = "commit_previous_turn_to_memory"
            debug_print("MasterAgent: Overriding to commit_previous_turn_to_memory due to exact 'remember this' match.")
        # --- End override --- 

        if agent_choice == "search":
            response_content = await self.search_agent.process(query_for_agent)
        elif agent_choice == "email":
            response_content = await self.email_agent.process(parameters)
        elif agent_choice == "calculator":
            response_content = await self.calculator_agent.process(query_for_agent)
        elif agent_choice == "camera":
            response_content = await self.camera_agent.process(query_for_agent)
        elif agent_choice == "weather":
            response_content = await self.weather_agent.process(query_for_agent)
        elif agent_choice == "browser": 
            response_content = await self.browser_agent.process(query_for_agent)
        # Add routing for screen agent if it exists
        # elif agent_choice == "screen":
        #     if hasattr(self, 'screen_agent') and self.screen_agent:
        #         response_content = await self.screen_agent.process(query_for_agent)
        #     else:
        #         response_content = "The screen agent is not available or not initialized."
        #         debug_print("MasterAgent: Screen agent called but not initialized or available.")
        elif agent_choice == "memory":
            if action_type == "commit_previous_turn_to_memory":
                if len(self.conversation_history) >= 2 and self.conversation_history[-2]["role"] == "assistant":
                    item_to_remember = ""
                    for i in range(len(self.conversation_history) - 2, -1, -1):
                        if self.conversation_history[i]["role"] == "assistant":
                            item_to_remember = self.conversation_history[i]["content"]
                            break
                    
                    if item_to_remember:
                        self._persist_memory_item(category="user_initiated_saves", item_content=item_to_remember)
                        response_content = f"Okay, I've remembered that: '{item_to_remember[:100].replace('\n', ' ')}...'"
                    else:
                        response_content = "There wasn't a clear previous message for me to remember. What would you like me to save?"
                else:
                    response_content = "There's no prior conversation for me to remember yet. What would you like me to save?"
            
            elif action_type == "commit_structured_fact":
                entity = parameters.get("entity")
                attribute = parameters.get("attribute")
                value = parameters.get("value")
                if entity and attribute and value:
                    fact_data = {"entity": entity, "attribute": attribute, "value": value}
                    self._persist_memory_item(category="fact_store", item_content=fact_data, is_fact_store_item=True)
                    response_content = f"Okay, I've recorded that {entity}'s {attribute} is {value}."
                else:
                    missing_params = []
                    if not entity: missing_params.append("entity (e.g., person, item)")
                    if not attribute: missing_params.append("attribute (e.g., email, color)")
                    if not value: missing_params.append("value (the actual data)")
                    response_content = f"I tried to save that fact, but I'm missing some details: { ', '.join(missing_params) }."

            elif action_type == "query_memory":
                # Basic retrieval from 'user_initiated_saves' for now
                # TODO: Enhance to query 'fact_store' based on entity/attribute from parameters
                query_entity = parameters.get("entity")
                query_attribute = parameters.get("attribute")
                
                found_facts = []
                if query_entity and "fact_store" in self.memory_data:
                    for fact in reversed(self.memory_data["fact_store"]):
                        if fact.get("entity", "").lower() == query_entity.lower():
                            if query_attribute and fact.get("attribute", "").lower() == query_attribute.lower():
                                found_facts.append(f"{fact['entity']}'s {fact['attribute']} is {fact['value']} (Saved on {fact['timestamp']}).")
                                break # Found specific attribute, stop
                            elif not query_attribute: # if no specific attribute, list all for entity
                                found_facts.append(f"{fact['entity']}'s {fact['attribute']} is {fact['value']} (Saved on {fact['timestamp']}).")
                    if found_facts:
                        response_content = "Here's what I found in my recorded facts:\n" + "\n".join(found_facts)
                    else:
                        response_content = f"I don't have any recorded facts for '{query_entity}'" 
                        if query_attribute: response_content += f" with attribute '{query_attribute}'."
                        else: response_content += "."

                elif "user_initiated_saves" in self.memory_data and self.memory_data["user_initiated_saves"]:
                    response_items = []
                    for item in self.memory_data["user_initiated_saves"][-3:]: # Show last 3 saved items
                        response_items.append(f"- (Saved on {item['timestamp']}): {item['content'][:150].replace('\n', ' ')}...")
                    response_content = "I don't have specific facts for that query, but here are some of the recent general things I've remembered for you:\n" + "\n".join(response_items)
                else:
                    response_content = "I haven't specifically remembered anything for you yet. Ask me to 'remember this' after I provide useful info, or 'remember Kiki\'s email is ...' to store a fact!"
            else:
                response_content = "I can help you remember things or recall saved information. How can I assist?"

        elif agent_choice == "master_agent_direct":
            response_content = await super().process(user_input)
        else:
             debug_print(f"MasterAgent: Unknown agent choice '{agent_choice}', falling back to master agent direct.")
             response_content = await super().process(user_input) # Fallback to master agent

        self.conversation_history.append({"role": "assistant", "content": response_content})
        return response_content

    def save_full_conversation_history(self):
        """Explicitly saves the entire current conversation history to the memory file."""
        if self.conversation_history:
            self._persist_memory_item(category="conversation_history", item_content=self.conversation_history)
            debug_print("MasterAgent: Full conversation history saved.")
        else:
            debug_print("MasterAgent: No conversation history to save.")

    def load_initial_conversation_history(self):
        """Loads conversation history from memory_data if available."""
        if isinstance(self.memory_data, dict) and "conversation_history" in self.memory_data:
            loaded_history = self.memory_data["conversation_history"]
            if isinstance(loaded_history, list):
                self.conversation_history = loaded_history
                debug_print(f"MasterAgent: Loaded {len(loaded_history)} items from persistent conversation history.")
            else:
                debug_print("MasterAgent: conversation_history in memory file is not a list. Starting fresh.")
        else:
            debug_print("MasterAgent: No persistent conversation history found in memory file.")


from agents.search_agent import SearchAgent
from agents.email_agent import EmailAgent
from agents.calculator_agent import CalculatorAgent
from agents.weather_agent import WeatherAgent
from config.settings import debug_print
from typing import Optional
# Ensure BaseAgent is imported if not already implicitly done through a parent class in full context
# from .base_agent import BaseAgent # Assuming BaseAgent is in the same directory or accessible 