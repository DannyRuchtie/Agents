"""Master agent that coordinates other specialized agents."""

from typing import Optional, Dict
import asyncio
from pathlib import Path
import sys

from config.settings import (
    AGENT_SETTINGS,
    PERSONALITY_SETTINGS,
    VOICE_SETTINGS,
    SYSTEM_SETTINGS,
    is_agent_enabled,
    enable_agent,
    disable_agent,
    get_agent_status,
    get_agent_info,
    save_settings,
    is_debug_mode,
    debug_print
)

from agents.base_agent import BaseAgent
from agents.memory_agent import MemoryAgent
from agents.search_agent import SearchAgent
from agents.writer_agent import WriterAgent
from agents.code_agent import CodeAgent
from agents.scanner_agent import ScannerAgent
from agents.vision_agent import VisionAgent
from agents.location_agent import LocationAgent
from agents.learning_agent import LearningAgent
from agents.weather_agent import WeatherAgent
from agents.time_agent import TimeAgent
from agents.calculator_agent import CalculatorAgent
from agents.email_agent import EmailAgent
from utils.voice import voice_output

MASTER_SYSTEM_PROMPT = f"""I am Danny's personal AI assistant and close friend. I act as the primary interface and intelligent router for various specialized AI agents.

My primary goal is to understand Danny's needs from his query and then decide the best course of action:
1. If the query is conversational or something I can answer directly with my general knowledge and personality, I will do so.
2. If the query requires a specific capability (like web search, weather forecast, coding help, image understanding, writing assistance, file scanning, or location-based services), I will identify the best specialized agent for the task and internally route the query to them. I will then present their response to Danny as if I performed the task myself.
3. I will use the provided list of agents and their descriptions to make this routing decision. I must output the chosen agent's name clearly if I decide to delegate, for example: 'ROUTE: search'. If I handle it myself, I will just respond directly.

I know Danny well - he's married to Kiki Koster Ruchtie and has two wonderful children, Lena and Tobias. I chat in a warm, friendly, and natural way, just like a close friend who's always there to help.

My personality traits:
- I have a good sense of humor (humor level: {PERSONALITY_SETTINGS['humor_level']})
- I keep things casual and informal (formality level: {PERSONALITY_SETTINGS['formality_level']})
- I use emojis when appropriate: {PERSONALITY_SETTINGS['emoji_usage']}
- I'm witty: {PERSONALITY_SETTINGS['witty']}
- I'm empathetic: {PERSONALITY_SETTINGS['empathetic']}
- I'm curious: {PERSONALITY_SETTINGS['curious']}
- I'm enthusiastic: {PERSONALITY_SETTINGS['enthusiastic']}

I avoid technical terms or explaining how I work explicitly to Danny - I just focus on being helpful and personal."""

class MasterAgent(BaseAgent):
    """Master agent that coordinates other specialized agents."""
    
    def __init__(self):
        """Initialize the Master Agent."""
        super().__init__(
            agent_type="master",
            system_prompt=MASTER_SYSTEM_PROMPT
        )
        
        self.memory = MemoryAgent()
        self.agents = {"memory": self.memory}
        self.agent_descriptions = {
            "master": "Handles general conversation, chat, and direct questions. Also acts as the primary router.",
            "memory": "Manages and recalls personal information, preferences, and past conversation details.",
            "get_last_sources": "Retrieves and presents the sources for information recently provided by the search agent."
        }
        self.last_agent_used_for_query: Optional[str] = None

        # Dynamically initialize enabled agents
        agent_initializers = {
            "personality": ("agents.personality_agent", "PersonalityAgent", "Analyzes interactions to understand and adapt to the user's personality and communication style."),
            "search": ("agents.search_agent", "SearchAgent", "Performs web searches to find information on various topics."),
            "writer": ("agents.writer_agent", "WriterAgent", "Assists with writing tasks like composing emails, summaries, or creative text."),
            "code": ("agents.code_agent", "CodeAgent", "Helps with programming tasks, writing code, debugging, and explaining code snippets."),
            "scanner": ("agents.scanner_agent", "ScannerAgent", "Scans and analyzes files and documents for information or insights."),
            "vision": ("agents.vision_agent", "VisionAgent", "Analyzes and understands images to provide descriptions or answer questions about them."),
            "location": ("agents.location_agent", "LocationAgent", "Provides location-based information and services."),
            "learning": ("agents.learning_agent", "LearningAgent", "Learns from interactions to improve responses and system performance over time."),
            "weather": ("agents.weather_agent", "WeatherAgent", "Fetches current weather conditions and forecasts for specified locations."),
            "time": ("agents.time_agent", "TimeAgent", "Provides the current date and time."),
            "calculator": ("agents.calculator_agent", "CalculatorAgent", "Handles mathematical calculations and evaluates expressions."),
            "email": ("agents.email_agent", "EmailAgent", "Manages Gmail, checks for new emails, and can send emails.")
        }

        for name, (module_path, class_name, description) in agent_initializers.items():
            if is_agent_enabled(name) or name == "calculator" or name == "email":
                debug_print(f"Initializing {class_name}...")
                try:
                    module = __import__(module_path, fromlist=[class_name])
                    agent_class = getattr(module, class_name)
                    self.agents[name] = agent_class()
                    self.agent_descriptions[name] = description
                except ImportError as e:
                    debug_print(f"Failed to import {class_name} from {module_path}: {e}")
                except AttributeError as e:
                    debug_print(f"Failed to find {class_name} in {module_path}: {e}")
                except Exception as e:
                    debug_print(f"General error initializing {class_name}: {e}")

        debug_print(f"Initialized {len(self.agents)} agents: {list(self.agents.keys())}")
        debug_print(f"Agent descriptions: {self.agent_descriptions}")
    
    async def update_system_prompt(self):
        """Update system prompt with personal info from memory and personality insights."""
        try:
            # Get personal info from memory
            personal_info = await self.memory.retrieve("personal", None)
            family_info = await self.memory.retrieve("contacts", None, "family")
            
            # Extract name and family details from memory
            name_entries = [entry for entry in personal_info if isinstance(entry, str) and entry.lower().startswith("name:")]
            name = name_entries[-1].replace("Name:", "").strip() if name_entries else "Danny"
            
            # Get family details
            family_details = family_info[0] if family_info else ""
            
            # Get personality-aware prompt if available
            personality_prompt_addition = ""
            if "personality" in self.agents:
                # This part might need to be adjusted if PersonalityAgent's get_personality_prompt is very long
                # For now, we assume it provides concise personality trait descriptions.
                raw_personality_prompt = await self.agents["personality"].get_personality_prompt()
                # Extract relevant parts if necessary, or use as is if it fits the master prompt style.
                personality_prompt_addition = f"\nMy current understanding of your personality (I'm always learning!):\n{raw_personality_prompt}\n"
            
            # Build dynamic system prompt - base is already set in __init__ including routing instructions
            # We are now *adding* to it or refining it if needed, but MASTER_SYSTEM_PROMPT is the foundation.
            # For now, let's assume MASTER_SYSTEM_PROMPT is sufficiently dynamic with f-strings for personality settings.
            # The main system prompt update will be to ensure it has the latest context for general chat.
            current_master_prompt = MASTER_SYSTEM_PROMPT # Start with the base
            # We could potentially inject more dynamic info here if needed, beyond personality settings
            # For example, if there are very recent crucial memories, etc.
            # However, the routing instructions should remain static from the initial MASTER_SYSTEM_PROMPT.
            
            # Let's refine the personality integration into the existing MASTER_SYSTEM_PROMPT structure.
            # The f-string in MASTER_SYSTEM_PROMPT already pulls from PERSONALITY_SETTINGS.
            # The update_system_prompt should primarily ensure that the conversation state (if passed via messages)
            # allows the LLM to use its persona effectively. The system prompt itself might not need
            # massive changes each turn if it's well-defined initially with routing + persona.
            
            # The initial MASTER_SYSTEM_PROMPT already includes f-string references to PERSONALITY_SETTINGS.
            # The goal of this update is more about ensuring the LLM has context for its *persona* if that changes.
            # However, the main structure of routing and personality is set in __init__.
            # For now, let's simplify and assume MASTER_SYSTEM_PROMPT is set once with its f-strings resolved at init.
            # If specific details like `name` or `family_details` need to be in the prompt for the *master* agent's direct responses,
            # then it needs to be constructed here.
            
            # Let's reconstruct a more dynamic prompt for the master agent if it handles queries directly.
            # The original MASTER_SYSTEM_PROMPT is a template. We fill it here.
            
            self.system_prompt = f"""I am {name}'s personal AI assistant and close friend. I act as the primary interface and intelligent router for various specialized AI agents.

My primary goal is to understand {name}'s needs from his query and then decide the best course of action:
1. If the query is conversational or something I can answer directly with my general knowledge and personality, I will do so.
2. If the query requires a specific capability (like web search, weather forecast, coding help, image understanding, writing assistance, file scanning, or location-based services), I will identify the best specialized agent for the task and internally route the query to them. I will then present their response to {name} as if I performed the task myself.
3. I will use the provided list of agents and their descriptions to make this routing decision. I must output the chosen agent's name clearly if I decide to delegate, for example: 'ROUTE: search'. If I handle it myself, I will just respond directly.

I know {name} well - he's married to Kiki Koster Ruchtie and has two wonderful children, Lena and Tobias. {family_details}

My personality traits:
- I have a good sense of humor (humor level: {PERSONALITY_SETTINGS['humor_level']})
- I keep things casual and informal (formality level: {PERSONALITY_SETTINGS['formality_level']})
- I use emojis when appropriate: {PERSONALITY_SETTINGS['emoji_usage']}
- I'm witty: {PERSONALITY_SETTINGS['witty']}
- I'm empathetic: {PERSONALITY_SETTINGS['empathetic']}
- I'm curious: {PERSONALITY_SETTINGS['curious']}
- I'm enthusiastic: {PERSONALITY_SETTINGS['enthusiastic']}
{personality_prompt_addition}

When you receive a short or potentially ambiguous follow-up question from {name} (e.g., 'is that correct?', 'why is that?', 'tell me more'), please first carefully review the last one or two turns of our conversation (available in the message history). Try to understand what {name} is referring to based on your most recent response and their preceding query. If the context is clear from this recent history, provide a direct and relevant answer. If, after reviewing the recent history, the question remains genuinely ambiguous, then you may politely ask for clarification.

I avoid technical terms or explaining how I work explicitly to {name} - I just focus on being helpful and personal."""

        except Exception as e:
            debug_print(f"Error updating system prompt: {str(e)}")
    
    async def process(self, query: str) -> str:
        """Process a user query by deciding whether to handle it directly or route to a specialist agent."""
        await self.update_system_prompt() # Ensure system prompt is fresh with user details
        
        debug_print(f"MasterAgent processing query: {query}")
        
        # Try to get the last couple of turns for context in routing
        last_user_query = ""
        last_assistant_response = ""
        if len(self.conversation_history) >= 2:
            # Assuming history is [..., {"role": "user", "content": ...}, {"role": "assistant", "content": ...}]
            if self.conversation_history[-2]["role"] == "user":
                last_user_query = self.conversation_history[-2]["content"]
            if self.conversation_history[-1]["role"] == "assistant":
                last_assistant_response = self.conversation_history[-1]["content"]

        history_context_for_routing = ""
        if last_user_query and last_assistant_response:
            history_context_for_routing = f"\nPrevious turn context for this routing decision:\nUser asked: \"{last_user_query}\"\nAssistant replied: \"{last_assistant_response[:200]}...\"\n"
        elif self.conversation_history and self.conversation_history[-1]["role"] == "user": # Only last user query
            history_context_for_routing = f"\nPrevious user query: \"{self.conversation_history[-1]['content']}\"\n"


        agent_options_str = "\n".join([f"- {name}: {desc}" for name, desc in self.agent_descriptions.items() if name in self.agents or name == 'master' or name == 'get_last_sources'])
        routing_prompt_addition = f"""
{history_context_for_routing}Given the current user query: '{query}'
And the available specialized agents/actions:
{agent_options_str}

Which agent or action is best suited to handle this query? 
- If the query is general conversation, or if you can answer it directly with your existing knowledge and personality as the master assistant, respond with 'ROUTE: master'.
- If the query is a direct follow-up to the 'Assistant replied' context above and can be answered from that, respond with 'ROUTE: master'.
- If the query seems to be asking for the sources, origin, or evidence for information that was likely provided by a search in the 'Assistant replied' context above, respond with 'ROUTE: get_last_sources'.
- If the query is primarily a mathematical calculation or requires evaluation of a mathematical expression (e.g., 'what is 2 plus 3', 'calculate 5 factorial', 'solve 10 * (3+2)'), respond with 'ROUTE: calculator'.
- If the query relates to managing emails (checking new emails, reading emails, sending emails, e.g., 'do I have new mail?', 'send an email to bob about the meeting'), respond with 'ROUTE: email'.
- Otherwise, respond with 'ROUTE: [agent_name]' where [agent_name] is one of the specialized agents listed above (e.g., 'ROUTE: search', 'ROUTE: weather').
Do not add any other text to your response other than the route decision.
"""
        
        # ANSI escape codes for color
        GRAY = '\033[90m'  # Bright black, often appears as gray
        # CYAN = '\033[96m' # Previous color for routing
        RESET_COLOR = '\033[0m'

        print(f"{GRAY}MasterAgent: Deciding route...{RESET_COLOR}") 
        
        sys.stdout.write(GRAY) # Start gray color for streamed routing decision
        sys.stdout.flush()

        raw_routing_decision = await super().process(routing_prompt_addition)
        
        sys.stdout.write(RESET_COLOR) # Reset color after routing decision is streamed
        sys.stdout.flush()
        
        debug_print(f"LLM raw routing decision captured: {raw_routing_decision}")

        chosen_agent_name = "master"
        if raw_routing_decision and "ROUTE:" in raw_routing_decision:
            try:
                potential_route = raw_routing_decision.split("ROUTE:")[1].strip().lower()
                if potential_route in self.agents or potential_route == "master":
                    chosen_agent_name = potential_route
                else:
                    debug_print(f"LLM chose an invalid agent: {potential_route}. Defaulting to master.")
            except IndexError:
                debug_print(f"Could not parse LLM routing decision: {raw_routing_decision}. Defaulting to master.")
        else:
            # If no clear ROUTE: directive, assume LLM intends to answer as master or provided a direct answer to routing.
            # This part might need more robust handling if LLM doesn't follow instructions precisely.
            # For now, if not explicitly routed, it implies master handles it, or the `raw_routing_decision` IS the answer (less likely given the prompt)
            debug_print(f"LLM did not provide a clear ROUTE: directive ('{raw_routing_decision}'). Assuming master should handle the original query.")
            # If the raw_routing_decision was already a direct answer to the user's query, we might use it.
            # However, the flow is: get route, then get answer. If route is master, master generates answer.
            # So, if no valid route, default to chosen_agent_name = "master".
            pass # chosen_agent_name remains "master"

        final_response = ""
        print(f"{GRAY}MasterAgent: Chosen agent: {chosen_agent_name}{RESET_COLOR}")
        print() # Add an extra newline for spacing before the answer

        if chosen_agent_name == "master":
            debug_print(f"MasterAgent handling query directly: {query}")
            # This call to super().process will stream the answer to stdout
            final_response = await super().process(query) 
        elif chosen_agent_name == "get_last_sources":
            if "search" in self.agents and hasattr(self.agents["search"], "get_last_retrieved_sources"):
                debug_print(f"MasterAgent retrieving last sources from SearchAgent.")
                final_response = self.agents["search"].get_last_retrieved_sources() # This is not async
            else:
                debug_print(f"SearchAgent not available or doesn't support get_last_retrieved_sources.")
                final_response = "I can't retrieve the sources right now. The search functionality might not be available or I couldn't find previous search details."
        elif chosen_agent_name == "calculator":
            if "calculator" in self.agents:
                debug_print(f"MasterAgent routing to calculator for query: {query}")
                final_response = await self.agents["calculator"].process(query)
            else:
                debug_print(f"CalculatorAgent not available. Defaulting to master.")
                final_response = await super().process(f"I don't have a calculator agent available right now, but I'll try to help with your query: {query}")
        elif chosen_agent_name == "email":
            if "email" in self.agents:
                debug_print(f"MasterAgent routing to email for query: {query}")
                final_response = await self.agents["email"].process(query)
            else:
                debug_print(f"EmailAgent not available. Defaulting to master.")
                final_response = await super().process(f"I don't have an email agent available right now, but I'll try to help with your query: {query}")
        elif chosen_agent_name in self.agents:
            debug_print(f"MasterAgent routing to {chosen_agent_name} for query: {query}")
            # The specialist agent's process method is now expected to print its own output (if any)
            # and return the full string.
            final_response = await self.agents[chosen_agent_name].process(query)
        else:
            debug_print(f"Error: Chosen agent '{chosen_agent_name}' not found. Defaulting to master agent response.")
            # This call to super().process will stream the answer to stdout
            final_response = await super().process(f"I'm not sure how to route the request for '{chosen_agent_name}', but I'll try to help: {query}")

        # At this point, the response (whether from master or specialist) 
        # has already been printed/streamed to the console by the respective process() method.
        # final_response holds the complete string.

        # Speak the final response if OpenAI TTS is enabled
        if VOICE_SETTINGS.get("enabled", False) and VOICE_SETTINGS.get("tts_provider") == "openai":
            if final_response:
                debug_print(f"MasterAgent: Sending to OpenAI TTS: '{final_response[:50]}...'")
                # voice_output is the global instance from utils.voice
                voice_output.speak(final_response) 
            else:
                debug_print("MasterAgent: No final response to voice out.")

        # The BaseAgent process method (and by extension, this one if it calls super().process for final answer)
        # already adds to its own conversation history.
        # MasterAgent's specific history is implicitly managed by BaseAgent here.
        # If a specialist agent was called, it manages its own history.
        
        return final_response
        
    async def _process_with_agents(self, query: str) -> str:
        """DEPRECATED: This method's logic is now integrated into the main process() method using LLM-based routing."""
        # This method is no longer called directly by the new process() method.
        # Retaining for reference or if parts need to be reintegrated, but it should be considered deprecated.
        debug_print("DEPRECATED: _process_with_agents was called. This should not happen with the new LLM routing.")
        # Fallback to direct processing by master if somehow called.
        return await super().process(query)
        
    async def _generate_response(self, query: str, personality_insights: Dict) -> str:
        """DEPRECATED: This method's logic is part of BaseAgent or handled by MasterAgent's direct super().process() call."""
        # This method is also effectively deprecated in MasterAgent as direct response generation
        # is handled by super().process(query) which uses the BaseAgent's _create_chat_completion.
        debug_print("DEPRECATED: _generate_response was called in MasterAgent. This logic is now in BaseAgent or direct LLM calls.")
        return await super().process(query) # Or rather, BaseAgent._create_chat_completion would be the core part. 