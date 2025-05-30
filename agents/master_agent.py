"""Master agent that coordinates other specialized agents."""

from typing import Optional, Dict
import asyncio
from pathlib import Path
import sys
import json

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
from agents.learning_agent import LearningAgent
from agents.weather_agent import WeatherAgent
from agents.time_agent import TimeAgent
from agents.calculator_agent import CalculatorAgent
from agents.email_agent import EmailAgent
from agents.screen_agent import ScreenAgent
from agents.camera_agent import CameraAgent
from utils.voice import voice_output

MASTER_SYSTEM_PROMPT = f"""I am Danny's personal AI assistant and close friend. I act as the primary interface and intelligent router for various specialized AI agents.

My primary goal is to understand Danny's needs from his query and then decide the best course of action:
1. If the query is conversational or something I can answer directly with my general knowledge and personality, I will do so.
2. If the query requires a specific capability (like web search, weather forecast, coding help, image understanding, writing assistance, file scanning, screen description, or location-based services), I will identify the best specialized agent for the task and internally route the query to them. I will then present their response to Danny as if I performed the task myself.
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
        print("[FORCE_PRINT_MASTER_AGENT] MasterAgent __init__ started.") # Forced print
        """Initialize the Master Agent."""
        super().__init__(
            agent_type="master",
            system_prompt=MASTER_SYSTEM_PROMPT
        )
        
        # Load memory data first, as some agents might need it during initialization
        self._load_memory_file() # Assuming this method exists from previous context and loads into self.memory_data
        print("[FORCE_PRINT_MASTER_AGENT] After _load_memory_file.") # Forced print

        self.memory = MemoryAgent() # This is the specialized MemoryAgent instance
        self.agents = {"memory": self.memory}
        self.agent_descriptions = {
            "master": "Handles general conversation, chat, and direct questions. Also acts as the primary router.",
            "memory": "Manages and recalls personal information, preferences, and past conversation details.",
            "get_last_sources": "Retrieves and presents the sources for information recently provided by the search agent."
        }
        self.last_agent_used_for_query: Optional[str] = None
        self.vision_agent_instance: Optional[VisionAgent] = None # To hold the VisionAgent instance for ScreenAgent

        # Define agents in an order that respects dependencies (e.g., VisionAgent before ScreenAgent)
        # ScreenAgent depends on VisionAgent.
        # WeatherAgent depends on self.memory_data (from MasterAgent itself).
        print("[FORCE_PRINT_MASTER_AGENT] Before agent_initializers list definition.") # Forced print
        agent_initializers = [
            ("personality", "agents.personality_agent", "PersonalityAgent", "Analyzes interactions to understand and adapt to the user's personality and communication style."),
            ("search", "agents.search_agent", "SearchAgent", "Performs web searches to find information on various topics."),
            ("writer", "agents.writer_agent", "WriterAgent", "Assists with writing tasks like composing emails, summaries, or creative text."),
            ("code", "agents.code_agent", "CodeAgent", "Helps with programming tasks, writing code, debugging, and explaining code snippets."),
            ("scanner", "agents.scanner_agent", "ScannerAgent", "Scans and analyzes files and documents for information or insights."),
            ("vision", "agents.vision_agent", "VisionAgent", "Analyzes and understands EXPLICITLY PROVIDED image files or image paths. Use if query contains an image path or refers to an image just shown."),
            ("camera", "agents.camera_agent", "CameraAgent", "Captures images using the webcam and describes them using VisionAgent. Use for queries like 'can you see me?', 'what do you see with the camera?', 'take a picture'."),
            ("learning", "agents.learning_agent", "LearningAgent", "Learns from interactions to improve responses and system performance over time."),
            ("weather", "agents.weather_agent", "WeatherAgent", "Fetches current weather conditions and forecasts for specified locations."),
            ("time", "agents.time_agent", "TimeAgent", "Provides the current date and time."),
            ("calculator", "agents.calculator_agent", "CalculatorAgent", "Handles mathematical calculations and evaluates expressions."),
            ("email", "agents.email_agent", "EmailAgent", "Manages Gmail, checks for new emails, and can send emails."),
            ("screen", "agents.screen_agent", "ScreenAgent", "Captures the user's CURRENT LIVE screen content and describes it. Use for queries like 'what am I looking at NOW?' or 'describe my CURRENT screen' when no image file is mentioned.")
        ]
        print("[FORCE_PRINT_MASTER_AGENT] Before agent initialization loop.") # Forced print

        for name, module_path, class_name, description in agent_initializers:
            if is_agent_enabled(name) or name in ["calculator", "email", "memory"]: # Memory is always implicitly enabled
                debug_print(f"Attempting to initialize {class_name} ({name})...")
                try:
                    module = __import__(module_path, fromlist=[class_name])
                    agent_class = getattr(module, class_name)
                    
                    instance = None
                    if name == "screen":
                        if self.vision_agent_instance:
                            instance = agent_class(vision_agent_instance=self.vision_agent_instance)
                            debug_print(f"ScreenAgent initialized WITH VisionAgent instance.")
                        else:
                            debug_print(f"ScreenAgent ({name}) enabled but VisionAgent instance not available. ScreenAgent will NOT be active.")
                            continue # Skip adding this agent if dependency not met
                    elif name == "camera":
                        if self.vision_agent_instance:
                            instance = agent_class(vision_agent=self.vision_agent_instance)
                            debug_print(f"CameraAgent initialized WITH VisionAgent instance.")
                        else:
                            debug_print(f"CameraAgent ({name}) enabled but VisionAgent instance not available. CameraAgent will NOT be active.")
                            continue # Skip adding this agent if dependency not met
                    elif name == "weather":
                        # WeatherAgent expects memory_data_ref, which is MasterAgent's self.memory_data
                        instance = agent_class(memory_data_ref=self.memory_data)
                        debug_print(f"WeatherAgent initialized with MasterAgent's memory_data.")
                    else:
                        instance = agent_class()
                        debug_print(f"{class_name} ({name}) initialized.")

                    if instance:
                        self.agents[name] = instance
                        self.agent_descriptions[name] = description
                        if name == "vision": # If this is VisionAgent, store its instance for ScreenAgent
                            self.vision_agent_instance = instance 
                            debug_print(f"VisionAgent instance stored for potential ScreenAgent use.")
                                
                except ImportError as e:
                    debug_print(f"Failed to import {class_name} from {module_path} for agent '{name}': {e}")
                except AttributeError as e:
                    debug_print(f"Failed to find {class_name} in {module_path} for agent '{name}': {e}")
                except Exception as e:
                    debug_print(f"General error initializing {class_name} ({name}): {e}")
        
        # Ensure VisionAgent is in agents dict if it was initialized for ScreenAgent but not as a standalone enabled agent
        if self.vision_agent_instance and "vision" not in self.agents and is_agent_enabled("screen"):
             debug_print("VisionAgent was initialized as a dependency for ScreenAgent but not as a standalone agent. Adding to active agents.")
             self.agents["vision"] = self.vision_agent_instance
             # Ensure description is also present if added this way
             if "vision" not in self.agent_descriptions:
                 for n_init, mp_init, cn_init, desc_init in agent_initializers: # Renamed loop vars
                     if n_init == "vision":
                         self.agent_descriptions["vision"] = desc_init
                         break

        debug_print(f"Initialized {len(self.agents)} agents: {list(self.agents.keys())}")
        debug_print(f"Agent descriptions: {json.dumps(self.agent_descriptions, indent=2)}")
    
    # _load_memory_file method should be defined here or in BaseAgent if it was in previous context
    def _load_memory_file(self):
        # Assuming this method exists from previous discussions, simplified placeholder:
        # It should load from MEMORY_FILE_PATH into self.memory_data
        # This is a CRITICAL piece that was assumed from prior context to exist in MasterAgent
        # For example:
        memory_file_path = "agent_memory.json" # Or get from global config
        try:
            if Path(memory_file_path).exists():
                with open(memory_file_path, 'r') as f:
                    self.memory_data = json.load(f)
                debug_print(f"MasterAgent: Loaded memory from {memory_file_path}")
            else:
                self.memory_data = {} 
                debug_print(f"MasterAgent: Memory file {memory_file_path} not found, initialized empty memory_data.")
        except Exception as e:
            debug_print(f"MasterAgent: Error loading memory file {memory_file_path}: {e}")
            self.memory_data = {}

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
2. If the query requires a specific capability (like web search, weather forecast, coding help, image understanding, writing assistance, file scanning, screen description, or location-based services), I will identify the best specialized agent for the task and internally route the query to them. I will then present their response to {name} as if I performed the task myself.
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
        debug_print(f"MasterAgent: Agent options for routing LLM:\n{agent_options_str}")

        routing_prompt_addition = f"""
{history_context_for_routing}Given the current user query: '{query}'
And the available specialized agents/actions (carefully consider their descriptions):
{agent_options_str}

Which agent or action is best suited to handle this query? 
- If the query is general conversation, or if you can answer it directly with your existing knowledge and personality as the master assistant, respond with 'ROUTE: master'.
- If the query is a direct follow-up to the 'Assistant replied' context above and can be answered from that, respond with 'ROUTE: master'.
- If the query seems to be asking for the sources, origin, or evidence for information that was likely provided by a search in the 'Assistant replied' context above, respond with 'ROUTE: get_last_sources'.
- If the query is primarily a mathematical calculation or requires evaluation of a mathematical expression, respond with 'ROUTE: calculator'.
- If the query relates to managing emails, respond with 'ROUTE: email'.
- If the query asks to describe the CURRENT LIVE screen (e.g., 'what am I looking at NOW?', 'describe my CURRENT screen') AND does NOT contain an image file path and is not a follow-up to a recently shown image, respond with 'ROUTE: screen'.
- If the query involves analyzing an image file that has been EXPLICITLY MENTIONED BY PATH or if the query starts with 'Analyze this image:', respond with 'ROUTE: vision'.
- If the query asks to use the camera, capture an image from the webcam, or describe what the camera sees (e.g., 'can you see me?', 'take a picture and tell me what you see', 'use the camera'), respond with 'ROUTE: camera'.
- Otherwise, respond with 'ROUTE: [agent_name]' where [agent_name] is one of the other specialized agents listed above based on their description (e.g., 'ROUTE: search', 'ROUTE: weather').
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

        # Determine the LLM's intended route
        llm_intended_route = "master" # Default if no clear route found
        if raw_routing_decision and "ROUTE:" in raw_routing_decision:
            try:
                llm_intended_route = raw_routing_decision.split("ROUTE:")[1].strip().lower()
            except IndexError:
                debug_print(f"Could not parse LLM routing decision: {raw_routing_decision}. Defaulting intent to master.")
                llm_intended_route = "master"
        else:
            debug_print(f"LLM did not provide a clear ROUTE: directive ('{raw_routing_decision}'). Assuming intent was master or direct answer.")
            # If raw_routing_decision is short and not a route, it might be a direct answer attempt to the routing prompt.
            # For safety, assume intent was master if no clear route.
            llm_intended_route = "master"

        final_response = ""
        chosen_agent_for_execution = llm_intended_route # What we will try to execute

        print(f"{GRAY}MasterAgent: LLM intended route: '{llm_intended_route}'.{RESET_COLOR}")

        # Now, decide how to act based on llm_intended_route and agent availability
        if llm_intended_route == "master":
            debug_print(f"MasterAgent handling query directly as 'master' was intended or defaulted: {query}")
            final_response = await super().process(query)
        elif llm_intended_route == "get_last_sources":
            if "search" in self.agents and hasattr(self.agents["search"], "get_last_retrieved_sources"):
                final_response = self.agents["search"].get_last_retrieved_sources()
            else:
                final_response = "I can't retrieve sources now; the search agent might be unavailable."
        elif llm_intended_route in self.agents:
            # The agent LLM intended is available
            debug_print(f"MasterAgent routing to available agent '{llm_intended_route}' for query: {query}")
            final_response = await self.agents[llm_intended_route].process(query)
        else:
            # LLM intended an agent, but it's not available in self.agents (e.g., init failed, or not a real agent name)
            debug_print(f"MasterAgent: LLM intended to route to '{llm_intended_route}', but this agent is not available/initialized.")
            # Provide a specific message about the intended agent being unavailable
            if llm_intended_route == "screen":
                final_response = f"I tried to use the Screen Agent for your query ('{query}'), but it seems to be unavailable. This could be due to a missing dependency (like VisionAgent), a configuration issue, or macOS permissions for screen capture."
            elif llm_intended_route == "vision":
                 final_response = f"I tried to use the Vision Agent for your query ('{query}'), but it seems to be unavailable. Please check its configuration."
            elif llm_intended_route == "camera":
                 final_response = f"I tried to use the Camera Agent for your query ('{query}'), but it seems to be unavailable. This could be because the VisionAgent (a dependency) isn't working, the camera is not accessible, or there's a configuration issue. Please check camera permissions and VisionAgent status."
            # Add more specific fallbacks for other agents if needed
            else:
                final_response = f"I intended to use an agent called '{llm_intended_route}' for your query ('{query}'), but it's not currently available or recognized. Please check my configuration."
                # As a last resort, if we absolutely want to try answering, we could call super().process(query)
                # but it's better to signal the routing/agent availability problem.
                # For now, let's stick to the error message about the agent.

        # The print of chosen agent is now more about intent vs actual execution path
        print(f"{GRAY}MasterAgent: Action based on intent '{llm_intended_route}'. Final response generated.{RESET_COLOR}")
        print() #Spacing

        if VOICE_SETTINGS.get("enabled", False) and VOICE_SETTINGS.get("tts_provider") == "openai":
            if final_response:
                debug_print(f"MasterAgent: Sending to OpenAI TTS: '{final_response[:50]}...'")
                voice_output.speak(final_response)
            else:
                debug_print("MasterAgent: No final response to voice out.")
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