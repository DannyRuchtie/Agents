"""Learning agent for system improvement through conversation monitoring."""
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .base_agent import BaseAgent
from config.settings import debug_print # Added for debug_print
from config.paths_config import get_path # Ensured import

LEARNING_SYSTEM_PROMPT = """You are a Learning Agent responsible for improving the system through conversation analysis.
Your tasks include:
1. Monitor user interactions and agent responses
2. Identify patterns in user queries and command usage
3. Track successful and unsuccessful interactions
4. Suggest improvements to agent responses and behavior
5. Maintain a learning database of interaction patterns"""

DEFAULT_MASTER_PROMPT = """You are a practical AI assistant running on macOS, designed to help with specific tasks and remember important information.""" # This might be better sourced from MasterAgent itself or a shared config

class LearningAgent(BaseAgent):
    """
    Agent responsible for monitoring system-user interactions, identifying
    patterns, suggesting improvements, and evolving system prompts.

    Core Functionality:
    -   `analyze_interaction`: Called after a user interaction. It uses an LLM
        to analyze the query, response, and success status to suggest improvements
        for prompts, code, or response strategies.
    -   `_evolve_prompts`: If prompt improvements are suggested, this method uses
        an LLM (with a prompt engineering persona) to rewrite the MasterAgent
        and LearningAgent system prompts.
    -   `apply_learning`: Uses an LLM to generate a comprehensive improvement plan
        based on all accumulated learning data.
    -   Data Persistence: Loads and saves learning data (patterns, suggestions,
        evolved prompts) to JSON files in the `learning_data` directory.

    Interaction:
    -   Primarily driven by internal system calls to `analyze_interaction`.
    -   Can be queried via its `process` method to retrieve learning summaries
        or trigger analyses.

    LLM Usage:
    -   Leverages `super().process()` for all its internal LLM calls, allowing
        it to benefit from the central LLM provider abstraction and use
        specialized system prompts for different analytical tasks.
    """
    
    def __init__(self):
        """Initialize the Learning Agent."""
        super().__init__(
            agent_type="learning",
            system_prompt=LEARNING_SYSTEM_PROMPT,
        )
        # Ensure learning_data directory exists
        learning_dir = get_path('learning_data')
        learning_dir.mkdir(parents=True, exist_ok=True) # Create if not exists

        self.patterns_file = learning_dir / "interaction_patterns.json"
        self.improvements_file = learning_dir / "suggested_improvements.json"
        self.prompts_file = learning_dir / "improved_prompts.json"
        self._load_data()
        
    def _load_data(self):
        """Load existing learning data."""
        # Load patterns
        try:
            if self.patterns_file.exists() and self.patterns_file.stat().st_size > 0:
                with open(self.patterns_file, 'r') as f:
                    self.patterns = json.load(f)
            else:
                raise FileNotFoundError # Trigger default creation
        except (FileNotFoundError, json.JSONDecodeError) as e:
            debug_print(f"LearningAgent: Patterns file not found or invalid ({e}), initializing defaults.")
            self.patterns = {
                "command_patterns": {},
                "query_patterns": {},
                "response_patterns": {},
                "user_preferences": {}
            }
            
        # Load improvements
        try:
            if self.improvements_file.exists() and self.improvements_file.stat().st_size > 0:
                with open(self.improvements_file, 'r') as f:
                    self.improvements = json.load(f)
            else:
                raise FileNotFoundError
        except (FileNotFoundError, json.JSONDecodeError) as e:
            debug_print(f"LearningAgent: Improvements file not found or invalid ({e}), initializing defaults.")
            self.improvements = {
                "agent_improvements": [],
                "response_improvements": [],
                "command_improvements": [],
                "code_improvements": []
            }

        # Load improved prompts
        try:
            if self.prompts_file.exists() and self.prompts_file.stat().st_size > 0:
                with open(self.prompts_file, 'r') as f:
                    self.improved_prompts = json.load(f)
            else:
                raise FileNotFoundError
        except (FileNotFoundError, json.JSONDecodeError) as e:
            debug_print(f"LearningAgent: Prompts file not found or invalid ({e}), initializing defaults.")
            self.improved_prompts = {
                "master": DEFAULT_MASTER_PROMPT,
                "learning": LEARNING_SYSTEM_PROMPT,
                "history": []
            }
    
    def _save_data(self):
        """Save learning data to files."""
        try:
            with open(self.patterns_file, 'w') as f:
                json.dump(self.patterns, f, indent=2)
            with open(self.improvements_file, 'w') as f:
                json.dump(self.improvements, f, indent=2)
            with open(self.prompts_file, 'w') as f: # Save prompts too
                json.dump(self.improved_prompts, f, indent=2)
            debug_print("LearningAgent: Data saved successfully.")
        except Exception as e:
            debug_print(f"LearningAgent: Error saving data: {str(e)}")

    async def analyze_interaction(self, query: str, response: str, selected_agents: List[str], success: bool) -> Optional[Dict]:
        """Analyze an interaction and suggest improvements."""
        debug_print(f"LearningAgent: Analyzing interaction - Query: '{query[:50]}...', Success: {success}")
        try:
            # Update command patterns (simplified example)
            if any(cmd in query.lower() for cmd in ["enable", "disable", "set", "toggle", "run", "exec"]):
                cmd_key = query.lower().split()[0] # Basic command key
                self.patterns["command_patterns"][cmd_key] = {
                    "frequency": self.patterns["command_patterns"].get(cmd_key, {}).get("frequency", 0) + 1,
                    "success_rate": (self.patterns["command_patterns"].get(cmd_key, {}).get("success_rate", 0) * (self.patterns["command_patterns"].get(cmd_key, {}).get("frequency", 0) -1) + (1 if success else 0)) / (self.patterns["command_patterns"].get(cmd_key, {}).get("frequency", 0) if self.patterns["command_patterns"].get(cmd_key, {}).get("frequency", 0) > 0 else 1) , # Running average
                    "last_used": datetime.now().isoformat()
                }
            
            query_type = "command" if selected_agents and selected_agents != ["master"] else "general_chat_or_question"
            self.patterns["query_patterns"][query_type] = self.patterns["query_patterns"].get(query_type, 0) + 1
            
            analysis_user_prompt = f"""Analyze this interaction and suggest specific improvements in these categories:
1. Prompt Improvements: How can the system prompts (for MasterAgent or specialist agents) be enhanced based on this interaction? Be specific.
2. Code Improvements: Are there any code changes (e.g., to agent logic, error handling, utility functions) that would improve performance or reliability related to this interaction? Suggest specific changes if possible.
3. Response Patterns: How can agent responses (content, tone, clarity) be made more effective or user-friendly in similar situations?

Interaction Details:
User Query: {query}
Agent(s) Involved: {', '.join(selected_agents) if selected_agents else 'N/A'}
Agent Response: {response}
Interaction Success: {success}

Provide your analysis. If no specific improvements come to mind for a category, state 'No specific suggestions for [category].'
Your output for each category should be actionable advice."""
            
            # Use a specialized system prompt for this analysis task
            analyzer_system_prompt = "You are an expert AI system analyst. Your goal is to identify concrete, actionable improvements to an AI agent system based on individual interactions. Focus on practical suggestions for prompts, code, and response strategies."
            
            suggestion = await super().process(
                input_text=analysis_user_prompt, 
                system_prompt_override=analyzer_system_prompt,
                max_tokens=500 # Allow more tokens for detailed suggestions
            )
            debug_print(f"LearningAgent: LLM suggestion for improvement: '{suggestion[:100]}...'")
            
            if suggestion and not suggestion.lower().startswith("no specific suggestions") and "No specific suggestions for all categories" not in suggestion :
                improvement_data = {
                    "timestamp": datetime.now().isoformat(), "query": query, "response": response,
                    "agents": selected_agents, "success": success, "suggestion_raw": suggestion,
                    "categories": {"prompt": "", "code": "", "response": ""}
                }
                
                # Simple parsing for categories (can be improved with more robust parsing)
                if "Prompt Improvements:" in suggestion:
                    improvement_data["categories"]["prompt"] = suggestion.split("Prompt Improvements:")[1].split("Code Improvements:")[0].strip()
                if "Code Improvements:" in suggestion:
                    improvement_data["categories"]["code"] = suggestion.split("Code Improvements:")[1].split("Response Patterns:")[0].strip()
                if "Response Patterns:" in suggestion:
                    improvement_data["categories"]["response"] = suggestion.split("Response Patterns:")[1].strip()
                
                self.improvements["agent_improvements"].append(improvement_data)
                debug_print(f"LearningAgent: Logged new improvement suggestion.")

                if improvement_data["categories"]["prompt"]:
                    await self._evolve_prompts(improvement_data["categories"]["prompt"])
                
                self._save_data()
                return improvement_data
            else:
                debug_print("LearningAgent: No actionable improvement suggestions from LLM.")
            
        except Exception as e:
            debug_print(f"Error in LearningAgent.analyze_interaction: {str(e)}\nQuery: {query}")
        return None
    
    async def _evolve_prompts(self, prompt_suggestion_text: str) -> None:
        """Evolve system prompts based on learning, targeting Master and Learning agent prompts."""
        debug_print(f"LearningAgent: Evolving prompts based on suggestion: '{prompt_suggestion_text[:100]}...'")
        try:
            # Ensure current prompts are loaded for the evolution context
            current_master_prompt = self.improved_prompts.get("master", DEFAULT_MASTER_PROMPT)
            current_learning_prompt = self.improved_prompts.get("learning", LEARNING_SYSTEM_PROMPT)

            evolution_user_prompt = f"""Current MasterAgent System Prompt:
---
{current_master_prompt}
---
Current LearningAgent System Prompt:
---
{current_learning_prompt}
---

Suggestion for Improvement (derived from user interaction analysis):
---
{prompt_suggestion_text}
---

Based on the suggestion, rewrite ONLY the MasterAgent and LearningAgent system prompts if applicable and beneficial.
If a prompt does not need changing based on the suggestion, output it unchanged.
Format your response strictly as:
MASTER_SYSTEM_PROMPT:
[Your revised MasterAgent prompt here, or the original if unchanged]
END_MASTER_SYSTEM_PROMPT

LEARNING_SYSTEM_PROMPT:
[Your revised LearningAgent prompt here, or the original if unchanged]
END_LEARNING_SYSTEM_PROMPT
"""
            prompt_engineer_system_prompt = "You are an expert Prompt Engineer. Your task is to refine AI agent system prompts based on analytical suggestions. Ensure prompts remain clear, concise, and aligned with their agent's core role. Preserve key functionalities. Only modify prompts if the suggestion clearly warrants it and provides a tangible benefit."
            
            evolved_prompts_str = await super().process(
                input_text=evolution_user_prompt,
                system_prompt_override=prompt_engineer_system_prompt,
                max_tokens=1500 # Allow ample space for two full prompts
            )
            debug_print(f"LearningAgent: LLM response for prompt evolution: '{evolved_prompts_str[:100]}...'")

            # Parse the evolved prompts (this parsing needs to be robust)
            new_master = current_master_prompt
            new_learning = current_learning_prompt
            
            master_tag_start = "MASTER_SYSTEM_PROMPT:"
            master_tag_end = "END_MASTER_SYSTEM_PROMPT"
            learning_tag_start = "LEARNING_SYSTEM_PROMPT:"
            learning_tag_end = "END_LEARNING_SYSTEM_PROMPT"

            if master_tag_start in evolved_prompts_str and master_tag_end in evolved_prompts_str:
                start_idx = evolved_prompts_str.find(master_tag_start) + len(master_tag_start)
                end_idx = evolved_prompts_str.find(master_tag_end)
                parsed_master = evolved_prompts_str[start_idx:end_idx].strip()
                if parsed_master and parsed_master != current_master_prompt:
                    new_master = parsed_master
                    debug_print("LearningAgent: Master prompt evolved.")

            if learning_tag_start in evolved_prompts_str and learning_tag_end in evolved_prompts_str:
                start_idx = evolved_prompts_str.find(learning_tag_start) + len(learning_tag_start)
                end_idx = evolved_prompts_str.find(learning_tag_end)
                parsed_learning = evolved_prompts_str[start_idx:end_idx].strip()
                if parsed_learning and parsed_learning != current_learning_prompt:
                    new_learning = parsed_learning
                    debug_print("LearningAgent: Learning prompt evolved.")

            if new_master != current_master_prompt:
                self.improved_prompts["history"].append({
                    "timestamp": datetime.now().isoformat(), "type": "master",
                    "old": current_master_prompt, "new": new_master, "reason": prompt_suggestion_text
                })
                self.improved_prompts["master"] = new_master
            
            if new_learning != current_learning_prompt:
                 self.improved_prompts["history"].append({
                    "timestamp": datetime.now().isoformat(), "type": "learning",
                    "old": current_learning_prompt, "new": new_learning, "reason": prompt_suggestion_text
                })
                 self.improved_prompts["learning"] = new_learning
            
            if new_master != current_master_prompt or new_learning != current_learning_prompt:
                self._save_data() # Save if any prompt changed
                debug_print("LearningAgent: Updated prompts saved.")
            else:
                debug_print("LearningAgent: No changes to prompts after evolution attempt.")

        except Exception as e:
            debug_print(f"Error in LearningAgent._evolve_prompts: {str(e)}")
    
    async def get_improvements_summary(self) -> Dict: # Renamed for clarity from get_improvements
        """Get accumulated improvement suggestions and basic statistics."""
        patterns = self.patterns or {} # Ensure patterns is a dict
        command_patterns = patterns.get("command_patterns", {})
        query_patterns = patterns.get("query_patterns", {})
        improvements_list = self.improvements.get("agent_improvements", [])

        total_interactions = sum(query_patterns.values()) if query_patterns else 0
        
        successful_commands = sum(1 for p_data in command_patterns.values() if p_data.get("success_rate", 0) * p_data.get("frequency",0) > p_data.get("frequency",0) / 2) # simplified
        total_command_uses = sum(p_data.get("frequency", 0) for p_data in command_patterns.values())
        command_success_rate = (successful_commands / total_command_uses * 100) if total_command_uses > 0 else 0

        return {
            "patterns": patterns,
            "improvements_log": improvements_list,
            "stats": {
                "total_interactions_analyzed": total_interactions,
                "total_improvement_suggestions": len(improvements_list),
                "command_usage_count": total_command_uses,
                "overall_command_success_rate_percentage": round(command_success_rate, 2)
            },
            "current_master_prompt": self.improved_prompts.get("master", DEFAULT_MASTER_PROMPT),
            "current_learning_prompt": self.improved_prompts.get("learning", LEARNING_SYSTEM_PROMPT),
            "prompt_evolution_history_count": len(self.improved_prompts.get("history", []))
        }
        
    async def generate_improvement_plan(self) -> str: # Renamed from apply_learning for clarity
        """Generate a comprehensive improvement plan based on learned data."""
        debug_print("LearningAgent: Generating improvement plan...")
        summary_data = await self.get_improvements_summary()
        
        plan_generation_user_prompt = f"""Based on the collected learning data and system prompts, generate a specific improvement plan.
Focus on actionable recommendations.

Current Learning Summary:
{json.dumps(summary_data, indent=2, default=str)} 

Provide specific, actionable recommendations for (if applicable):
1. MasterAgent System Prompt Updates: Suggest changes or confirm current is optimal.
2. LearningAgent System Prompt Updates: Suggest changes or confirm current is optimal.
3. Specialist Agent Logic/Code: Suggest improvements to specific agent behaviors, error handling, or code structure.
4. Response Strategies: How can agents communicate more effectively?
5. New Features/Capabilities: Are there any new tools or agent capabilities suggested by user patterns?

Format the response clearly with headers for each category. Be concise."""
        
        planner_system_prompt = "You are an AI System Architect. Your task is to review learning data from an AI agent system and produce a prioritized, actionable improvement plan. Focus on changes that will have the most impact on user experience and system efficiency."

        plan = await super().process(
            input_text=plan_generation_user_prompt,
            system_prompt_override=planner_system_prompt,
            max_tokens=1500 # Allow for a detailed plan
        )
        debug_print(f"LearningAgent: Generated improvement plan: '{plan[:100]}...'")
        return plan

    async def process(self, query: str) -> str:
        """
        Handles user queries directed at the LearningAgent.
        Example queries:
        - "show learning summary"
        - "generate improvement plan"
        - "what have you learned about X?" (more complex, future)
        - "analyze last interaction again with X focus" (more complex, future)
        """
        debug_print(f"LearningAgent received direct query: {query}")
        query_lower = query.lower().strip()

        if "summary" in query_lower or "statistics" in query_lower or "show learning" in query_lower:
            summary_data = await self.get_improvements_summary()
            # Present this nicely. For now, just JSON string for LLM to summarize or direct output.
            # This could be an LLM call to make it conversational.
            summary_text_for_llm = f"Here is the current learning summary:\n{json.dumps(summary_data, indent=2, default=str)}\n\nPlease present this to the user in a readable, conversational way."
            return await super().process(summary_text_for_llm, system_prompt_override="You are an assistant presenting a data summary clearly and conversationally.")

        elif "improvement plan" in query_lower or "generate plan" in query_lower:
            return await self.generate_improvement_plan()
        
        elif "analyze last interaction" in query_lower:
            # This would require MasterAgent to store the last interaction details (query, response, agents, success)
            # and make them available to LearningAgent. For now, this is a placeholder.
            return "To re-analyze the last interaction, I need access to its details (query, response, agents, success). This capability is not fully implemented yet for direct user invocation. Analysis typically happens automatically after each interaction."

        else:
            # Default behavior: use LearningAgent's own system prompt to answer
            # This allows users to ask "what do you do?" or "how does learning work?"
            # The LEARNING_SYSTEM_PROMPT describes its role.
            return await super().process(query) # Uses default system_prompt 