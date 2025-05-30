import json
import datetime
import os

MEMORY_FILE_PATH = "agent_memory.json"

MASTER_SYSTEM_PROMPT = """You are a master AI agent coordinating a team of specialized AI agents.
Your primary role is to understand the user's request and route it to the most appropriate specialized agent.
Available agents and their functions:
- search: For web searches, finding information, or answering general knowledge questions.
- email: For managing Gmail, including checking new emails, sending emails, and searching for specific emails.
- calculator: For performing mathematical calculations.
- writer: For creative writing tasks, drafting documents, summarizing text.
- code: For generating code, explaining code, or helping with programming tasks.
- memory: For remembering specific pieces of information from the conversation when explicitly asked, or for retrieving previously remembered information.

Routing and Information Extraction:
Based on the user's query and the conversation history, determine the best agent.
Respond with a JSON object containing:
{
  "route_to_agent": "agent_name", // e.g., "search", "email", "memory"
  "action_type": "specific_action", // e.g., "web_search", "check_new_emails", "commit_previous_turn_to_memory", "general_query"
  "parameters": { // agent-specific parameters
    "query_for_agent": "full user query or modified query for the agent",
    // ... other parameters like search_terms, recipient, etc.
  },
  "explanation": "Brief explanation of why this agent and action were chosen."
}

Specific Instructions for "memory" route:
- If the user says "remember this", "save this", "keep this in mind", or similar phrases implying they want to save the *immediately preceding assistant response*, set "action_type": "commit_previous_turn_to_memory". Do NOT ask what to remember; the context is the last assistant message.
- If the user asks "what did I ask you to remember?", "what's in your memory?", or wants to retrieve/query stored information, set "action_type": "query_memory".
- For other general interactions related to memory capabilities, set "action_type": "general_memory_interaction".

If routing to 'email' for sending, try to extract 'to', 'subject', 'body'.
If routing to 'email' for searching, try to extract 'search_terms'.
If routing to 'search', pass the user's query mostly as-is to 'query_for_agent'.

Use the conversation history to understand follow-up questions and context.
Prioritize direct agent routing if a specialized agent clearly fits.
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
        # self.memory_agent = MemoryAgent() # If we create a dedicated class

        self._load_memory_file() # Load memory at startup

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

    def _persist_memory_item(self, category: str, item_content: any):
        if not isinstance(self.memory_data, dict): # Ensure memory_data is a dict
            self.memory_data = {}
        
        if category not in self.memory_data:
            self.memory_data[category] = []
        
        # For conversation history, we might replace it entirely or append smartly
        if category == "conversation_history":
             self.memory_data[category] = item_content # Replace if it's the whole history
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
            
            try:
                action_details = json.loads(action_details_json_str)
            except json.JSONDecodeError:
                debug_print("MasterAgent: Failed to parse JSON from LLM routing. Falling back to general response.")
                response_content = await super().process(user_input)
                self.conversation_history.append({"role": "assistant", "content": response_content})
                return response_content

            agent_choice = action_details.get("route_to_agent")
            action_type = action_details.get("action_type")
            parameters = action_details.get("parameters", {})
            query_for_agent = parameters.get("query_for_agent", user_input)

            response_content = f"Could not route request: {agent_choice} with action {action_type}"

            if agent_choice == "search":
                response_content = await self.search_agent.process(query_for_agent)
            elif agent_choice == "email":
                response_content = await self.email_agent.process(query_for_agent)
            elif agent_choice == "calculator":
                response_content = await self.calculator_agent.process(query_for_agent)
            elif agent_choice == "memory":
                if action_type == "commit_previous_turn_to_memory":
                    if len(self.conversation_history) >= 2:
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
                elif action_type == "query_memory":
                    # Basic retrieval from 'user_initiated_saves' for now
                    if "user_initiated_saves" in self.memory_data and self.memory_data["user_initiated_saves"]:
                        response_items = []
                        for item in self.memory_data["user_initiated_saves"][-3:]: # Show last 3 saved items
                            response_items.append(f"- (Saved on {item['timestamp']}): {item['content'][:150].replace('\n', ' ')}...")
                        response_content = "Here are some of the recent things I've remembered for you:\n" + "\n".join(response_items)
                    else:
                        response_content = "I haven't specifically remembered anything for you yet. Ask me to 'remember this' after I provide useful info!"
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
from config.settings import debug_print
from typing import Optional
# Ensure BaseAgent is imported if not already implicitly done through a parent class in full context
# from .base_agent import BaseAgent # Assuming BaseAgent is in the same directory or accessible 