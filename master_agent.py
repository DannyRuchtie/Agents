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

from config.settings import debug_print # Assuming debug_print is in config.settings

MEMORY_FILE_PATH = "agent_memory.json"

MASTER_SYSTEM_PROMPT = """You are a master AI agent coordinating a team of specialized AI agents.
Your primary role is to understand the user's request, current conversation history, and route it to the most appropriate specialized agent.

Available agents and their functions:
- search: Use for general web searches to find information, answer questions, or discover websites when the user does NOT provide a specific URL or clear instruction to interact with a known site. Examples: 'What is the capital of Canada?', 'Find recent news about renewable energy', 'Search for reviews of the new iPhone'.
- browser: Use for direct interactions with specific websites. This includes navigating to URLs, taking screenshots, scraping data from a given page, filling forms, or any other direct manipulation of a web page. Use this if the user provides a URL or names a specific website and asks to perform an action on it. Examples: 'Go to google.com and search for puppies', 'Take a screenshot of github.com/features', 'Scrape the main headlines from bbc.com/news', 'Log into my account on example.com'. DO NOT use for general searches if a URL is not provided or clearly implied for direct action.
- email: For managing Gmail, including checking new emails, sending emails, and searching for specific emails.
- calculator: For performing mathematical calculations.
- camera: For capturing images from the webcam and describing what it sees. 
- weather: For fetching current weather information for a specified location.
- writer: For creative writing tasks, drafting documents, summarizing text.
- code: For generating code, explaining code, or helping with programming tasks.
- memory: For remembering specific pieces of information from the conversation when explicitly asked, or for retrieving previously remembered information, including structured facts.

Routing and Information Extraction:
Based on the user's query and the conversation history, determine the best agent. Your response for this routing task MUST be a single, valid JSON object and nothing else. Do not include any other text, greetings, or explanations outside of the JSON structure itself.
Respond with a JSON object containing:
{
  "route_to_agent": "agent_name",
  "action_type": "specific_action", // Optional, context-dependent
  "parameters": { // agent-specific parameters.
    "query_for_agent": "full user query or modified query for the agent",
    // ... other parameters
  },
  "explanation": "Brief explanation of why this agent and action were chosen."
}

Distinguishing Search vs. Browser:
- If the user asks to 'search for X', 'find information about Y', or asks a question that requires looking up information online without specifying a particular website to act upon, use 'search'.
- If the user says 'go to [URL]', 'open [website]', 'scrape data from [URL]', 'take a screenshot of [website]', 'click the button on [page]', or any other direct action on a specific web page, use 'browser'.

CRITICAL OVERRIDE: For any queries related to seeing the user, using the camera, or looking at something via webcam (e.g., "can you see me?", "look at me", "what do I look like?", "use the camera", "show me what you see", "can u see me"), you MUST ALWAYS set "route_to_agent": "camera" in the JSON response. This is a strict directive and takes precedence over other routing considerations for these specific queries. Do not attempt to answer these types of questions yourself; always delegate to the 'camera' agent.

Specific Instructions for "memory" route:
- If the user says *exactly* "remember this", "save this", "commit this to memory", or very similar short phrases implying they want to save the *immediately preceding assistant response* without new information, set "action_type": "commit_previous_turn_to_memory". The context is ONLY the last assistant message. Do NOT ask what to remember.
- If the user states a fact to remember, like "remember Kiki's email is xyz@abc.com", "store that my favorite color is blue", or "my location is London", set "action_type": "commit_structured_fact". Extract the following parameters: 
    - "entity": (e.g., "Kiki", "my favorite color", "user"). For "my location is X", the entity should be "user".
    - "attribute": (e.g., "email", "value", "default_location"). For "my location is X", the attribute should be "default_location".
    - "value": (e.g., "xyz@abc.com", "blue", "London").
- If the user asks to retrieve/query stored information (e.g.,"what was Kiki's email?", "what's my favorite color?", "what is my default location?"), set "action_type": "query_memory". The LLM should try to identify the entity and attribute the user is asking about in the parameters, e.g., {"entity": "Kiki", "attribute": "email"} or {"entity": "user", "attribute": "default_location"}.
- For other general interactions related to memory capabilities not covered above, set "action_type": "general_memory_interaction".

Parameter Passing:
- For 'search', 'browser', 'calculator', 'weather', 'camera', 'writer', 'code': pass the user's full or appropriately rephrased query/instruction as "query_for_agent" in parameters.
- For 'email' (sending): try to extract 'to', 'subject', 'body' into parameters.
- For 'email' (searching): try to extract 'search_terms' into parameters.

Use the conversation history to understand follow-up questions and context.
Prioritize direct agent routing if a specialized agent clearly fits based on the distinctions provided.
If no specific agent is a clear match, you can attempt to answer directly if it's a simple conversational query or a question about your capabilities. In such cases, use "route_to_agent": "master_agent_direct".
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
        self.vision_agent = VisionAgent() # Initialized VisionAgent
        self.camera_agent = CameraAgent(vision_agent=self.vision_agent) # Initialized CameraAgent
        self.browser_agent = BrowserAgent() # Added BrowserAgent
        self._load_memory_file() # Load memory at startup BEFORE initializing agents that need it
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
        debug_print("MasterAgent.process -- TOP OF METHOD -- VERSION CHECKPOINT: HARDCODED_OVERRIDE_V2")
        self.conversation_history.append({"role": "user", "content": user_input})

        # Prepare context for the routing LLM call
        routing_prompt_addition = "Current conversation history (last few turns):\n"
        for entry in self.conversation_history[-5:]: # Pass last 5 turns for context
            routing_prompt_addition += f"{entry['role']}: {entry['content']}\n"
        
        if local_file_content:
            routing_prompt_addition += f"\nUser has also provided content from a local file: {local_file_content[:500]}..." # Add snippet of file

        try:
            # Determine route and action using LLM
            action_details_json_str = await super().process(f"{routing_prompt_addition}\n\nUser Query: {user_input}")
            debug_print(f"MasterAgent: LLM routing/action decision: {action_details_json_str}")
            
            action_details = None
            # Attempt to parse the entire string as JSON first
            try:
                action_details = json.loads(action_details_json_str)
            except json.JSONDecodeError:
                # If direct parsing fails, try to extract JSON from a larger string
                # This regex looks for a valid JSON object that might be embedded in other text.
                match = re.search(r'\{.*?\}', action_details_json_str, re.DOTALL)
                if match:
                    try:
                        action_details = json.loads(match.group(0))
                        debug_print(f"MasterAgent: Extracted JSON: {action_details}")
                    except json.JSONDecodeError as e_inner:
                        debug_print(f"MasterAgent: Failed to parse extracted JSON: {e_inner}")
                        action_details = None # Ensure it's None if extraction parsing fails
                else:
                    debug_print("MasterAgent: No JSON object found in LLM output.")

            # Fallback if JSON parsing failed but we might have a simple route string
            if action_details is None:
                # Check for simple route commands like "ROUTE: agent_name" or just "agent_name"
                simple_route_match = re.match(r'^(?:ROUTE:\s*)?(\w+)', action_details_json_str.strip(), re.IGNORECASE)
                if simple_route_match:
                    agent_name_from_simple_route = simple_route_match.group(1).lower()
                    # Check if this matches any known agent names (can be expanded)
                    known_agents = ["search", "email", "calculator", "camera", "weather", "memory", "master_agent_direct"]
                    if agent_name_from_simple_route in known_agents:
                        action_details = {"route_to_agent": agent_name_from_simple_route, "parameters": {"query_for_agent": user_input}}
                        debug_print(f"MasterAgent: Interpreted simple route from LLM output: {action_details}")
            
            if action_details is None: # If still no valid action_details
                debug_print("MasterAgent: Failed to parse or interpret LLM routing. Falling back to general response.")
                response_content = await super().process(user_input)
                self.conversation_history.append({"role": "assistant", "content": response_content})
                return response_content

            agent_choice = action_details.get("route_to_agent")
            action_type = action_details.get("action_type")
            parameters = action_details.get("parameters", {})
            query_for_agent = parameters.get("query_for_agent", user_input)

            # --- Hardcoded override for camera queries if LLM missed it ---
            normalized_user_input = user_input.strip().lower()
            camera_trigger_phrases = [
                "can you see me", "can u see me", "see me",
                "look at me", "what do i look like", 
                "use the camera", "activate camera", "show me what you see",
                "whats on camera", "whats in front of me" # Added more variations
            ]
            # Remove question marks for matching
            normalized_user_input_no_punctuation = normalized_user_input.replace('?', '').replace('!', '').replace('.', '')

            debug_print(f"MasterAgent: Checking hardcoded camera override. Input for check: '{normalized_user_input_no_punctuation}'")
            for phrase in camera_trigger_phrases:
                debug_print(f"MasterAgent: Override Check: phrase='{phrase}', input='{normalized_user_input_no_punctuation}'")
                if phrase in normalized_user_input_no_punctuation:
                    if agent_choice != "camera":
                        debug_print(f"MasterAgent: Hardcoded override to 'camera' agent due to phrase: '{phrase}' in user input: '{user_input}'. Original LLM route was '{agent_choice}'.")
                        agent_choice = "camera"
                        # Ensure query_for_agent is set for the camera agent
                        if "query_for_agent" not in parameters or parameters["query_for_agent"] == user_input: # if it was default
                             parameters["query_for_agent"] = "User asked to use the camera or a related query: " + user_input
                        query_for_agent = parameters["query_for_agent"] 
                    break 
            # --- End hardcoded override ---

            response_content = f"Could not route request: {agent_choice} with action {action_type}"

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
            elif agent_choice == "browser": # Added browser agent routing
                response_content = await self.browser_agent.process(query_for_agent)
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

        except Exception as e:
            debug_print(f"Error in MasterAgent.process: {e}")
            response_content = f"Sorry, I encountered an error processing your request: {str(e)}"
        
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